import os
import copy
import logging
import shutil
import sys
import tempfile
import zipfile

from contextlib import contextmanager
from pkg_resources import Requirement
from setuptools.package_index import PackageIndex

from pkglib.six.moves import configparser  # @UnresolvedImport

from pkglib_util.cmdline import set_env
from plglib_testing.util import create_package_from_template

logging.basicConfig(level=logging.DEBUG)
logger = logging.root

from .util import PkgTemplate, run_in_subprocess
from .server import HTTPTestServer


SETUP_TMPL = """
from setuptools import setup
setup(
    name = "%(name)s",
    version = "%(version)s",
    url = 'http://xxx',
    author = 'me',
    author_email = 'me@me.example',
)
"""

_save_restore = True


def zipdir(path, zip_file):
    for root, _, files in os.walk(path):
        for f in files:
            zip_file.write(os.path.join(root, f))


def rezip_egg(pkg_location, output_to):
    output_to = os.path.join(output_to, os.path.basename(pkg_location))
    os.chdir(pkg_location)

    egg_file = zipfile.ZipFile(output_to, 'w')
    zipdir(os.path.curdir, egg_file)
    egg_file.close()

    return output_to


class LocalPyPi(HTTPTestServer):
    """ Abstract class for creating a working dir and virtualenv,
        setting up a PyPi instance in a thread,
        and providing an api accessor.
    """
    username = 'admin'
    password = 'password'
    hostname = '127.0.0.1'
    package_index = PackageIndex()

    def __init__(self, target_python=None, **kwargs):
        self.target_python = target_python or sys.executable
        super(LocalPyPi, self).__init__(**kwargs)

    def pre_setup(self):
        self.env = dict(os.environ)
        if "PYTHONPATH" in self.env:
            del self.env["PYTHONPATH"]

        existing_path = self.env.get("PATH")
        self.env["PATH"] = os.path.dirname(self.python)
        if existing_path:
            self.env["PATH"] = self.env["PATH"] + os.path.pathsep + existing_path

    def get_rc(self):
        """ return a ConfigParser rc for this instance
        """
        config = configparser.ConfigParser()
        config.add_section('server-login')
        config.set('server-login', 'repository', self.uri)
        config.set('server-login', 'username', self.username)
        config.set('server-login', 'password', self.password)
        return config

    def build_egg_from_source(self, pkg_location, output_to, python):
        try:
            temp = tempfile.mkdtemp()
            self.run(('%s setup.py bdist_egg --dist-dir=' + temp) % python,
                     cd=pkg_location, capture=True)
            files = os.listdir(temp)
            if len(files) != 1:
                raise RuntimeError("Error while generating egg file for: %s" % pkg_location)
            egg_file = os.path.join(temp, files[0])
            shutil.move(egg_file, output_to)
            return os.path.join(output_to, os.path.basename(egg_file))
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    def create_egg_for_package(self, pkg_location, output_to, python):
        assert os.path.isdir(pkg_location)

        if pkg_location.endswith(".egg"):
            return rezip_egg(pkg_location, output_to)
        else:
            return self.build_egg_from_source(pkg_location, output_to, python)

    def upload_requirement(self, work_dir, req, python):
        dest_dir = self.get_file_dir(req.project_name).strip()
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        def fetch_requirement(req, dest_dir, force_download):
            from setuptools.package_index import PackageIndex  # @Reimport
            from pkg_resources import working_set  # @Reimport  # NOQA
            i = PackageIndex()
            if force_download:
                [i.remove(i[req.key][0]) for _ in xrange(len(i[req.key]))]
                d = i.download(req, dest_dir)
            else:
                d = i.fetch_distribution(req, dest_dir, force_scan=True)
            d = getattr(d, 'location', d) if d else ''
            return (d if d else working_set.resolve([req])[0].location)
        with set_env(COVERAGE_DISABLE_WARNINGS="1"):
            fetched = run_in_subprocess(fetch_requirement, python=python, cd=self.workspace
                                        )(req, dest_dir, force_download=False)

            if not fetched or not os.path.exists(fetched):
                err_msg = "Unable to find requirement: %r\n%s" % (str(req), fetched)
                raise RuntimeError(err_msg)

            if os.path.isdir(fetched):
                fetched = self.create_egg_for_package(fetched, work_dir, python)

        print("Fetched %r" % fetched)
        return fetched

    def post_setup(self):
        """ Upload the dependencies for pkglib so dependent tools
            can bootstrap cwthemselves as well as run tests on
            generated packages
        """
        self.bootstrap_tagup(python=self.target_python)

    def bootstrap_tagup(self, python):
        work_dir = os.path.join(self.workspace, 'pkglib-deps')
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        with open(os.path.join(work_dir, '.pypirc'), 'wt') as rc_file:
            self.get_rc().write(rc_file)

        # XXX find a better way to pass in credentials
        new_env = copy.copy(dict(os.environ))
        new_env['HOME'] = work_dir

        if "PYTHONPATH" in new_env:
            del new_env["PYTHONPATH"]

        def get_pkglib_reqs():
            from pkglib.setuptools.dependency import get_all_requirements
            return [(dist.project_name, dist.version)
                    for dist in get_all_requirements(['pkglib', 'pytest', 'pytest-cov'], ignore_explicit_builtins=True)
                    if dist.project_name not in ['virtualenv', 'setuptools']]
        for name, version in run_in_subprocess(get_pkglib_reqs, python=python, cd=self.workspace)():
            # Quick hack to get the built eggs into the test PyPi instance.
            # We register with an empty package file then copy the files in manually
            # We may need pip and distribute if virtualenv installed old versions.
            # (should only occur when upgrading to new virtualenv).
            with open(os.path.join(work_dir, 'setup.py'), 'wb') as fp:
                setup_py = SETUP_TMPL % {'name': name, 'version': version}
                fp.write(setup_py.encode('utf-8'))

            cmd = 'cd %s; %s setup.py register' % (work_dir, python)
            out = self.run(cmd, capture=True, env=new_env)

            logger.debug(out)
            assert '200' in out
            self.upload_requirement(work_dir, Requirement.parse('%s==%s' % (name, version)), python)


def checkout_develop_upload(pypi, venv, vcs_uri=None, name=None):
    if vcs_uri is None:
        vcs_uri = venv.vcs_uri
    if name is None:
        name = venv.name
    workspace = venv.workspace
    python = venv.python
    venv.run("svn co %s %s" % (vcs_uri, name))
    venv.run("cd %s/%s/trunk; HOME=%s %s setup.py develop -i %s/simple/" %
             (workspace, name, workspace, python, pypi.uri), capture=True)
    venv.create_pypirc(pypi.get_rc())
    venv.run("cd %s/%s/trunk; HOME=%s %s setup.py bdist_egg register upload" %
             (workspace, name, workspace, python))


def create_pkg_raw(pypi, svn, name="acme.foo", metadata={}, dev=True, venv=None, **kwargs):
    """ creates a pkg """
    if not venv:
        venv = PkgTemplate(name=name, repo_base=svn.uri, metadata=metadata, dev=dev, **kwargs)
        vcs_uri = venv.vcs_uri
    else:
        vcs_uri, _ = create_package_from_template(venv,
                                                  name=name,
                                                  repo_base=svn.uri,
                                                  metadata=metadata,
                                                  dev=dev,
                                                  **kwargs)

    print("%s: stored at %s" % (name, vcs_uri))

    venv.run("svn import %s %s -m 'initial import'" % (name, vcs_uri), capture=True)
    # Now to check out to get subversion info
    venv.run("mv %s imported_%s" % (name, name))
    checkout_develop_upload(pypi, venv, vcs_uri, name)
    return venv



@contextmanager
def create_pkg(pypi, svn, name="acme.foo", metadata={}, dev=True, venv=None, **kwargs):
    """ creates a pkg in a workspace as a context mgr
    """
    with create_pkg_raw(pypi, svn, name=name, metadata=metadata, dev=dev,
                        venv=venv, **kwargs) as env:
        yield env


_counter = 0
def change_pkg(pypi, pkg_template):
    """Introduces a change to svn (creates a file "newfileN"), commits and uploads."""
    global _counter
    _counter += 1

    workspace = pkg_template.workspace
    name = pkg_template.name
    python = pkg_template.python

    filename = 'newfile%s' % _counter

    pkg_template.run("cd %s; svn co %s/trunk %s_changed" % (workspace, pkg_template.vcs_uri, name))
    pkg_template.run("cd %s/%s_changed; echo 'hello' >%s; svn add %s; "
                     "svn commit -m 'random change'" % (workspace, name, filename, filename))
    pkg_template.run("cd %s/%s_changed; HOME=%s %s setup.py develop -i %s"
                         % (workspace, name, workspace, python, pypi.uri))
    pkg_template.run("cd %s/%s_changed; HOME=%s %s setup.py bdist_egg register upload"
                         % (workspace, name, workspace, python))
