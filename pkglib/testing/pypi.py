import os
import copy
import logging
from contextlib import contextmanager
from ConfigParser import ConfigParser

from setuptools.package_index import PackageIndex
from path import path

logging.basicConfig(level=logging.DEBUG)
logger = logging.root

from util import PkgTemplate
from server import HTTPTestServer

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


class LocalPyPi(HTTPTestServer):
    """ Abstract class for creating a working dir and virtualenv,
        setting up a PyPi instance in a thread,
        and providing an api accessor.
    """
    username = 'admin'
    password = 'password'
    hostname = '127.0.0.1'
    package_index = PackageIndex()

    def get_rc(self):
        """ return a ConfigParser rc for this instance
        """
        config = ConfigParser()
        config.add_section('server-login')
        config.set('server-login', 'repository', self.uri)
        config.set('server-login', 'username', self.username)
        config.set('server-login', 'password', self.password)
        return config

    def upload_requirement(self, work_dir, req):
        dest_dir = self.get_file_dir(req.project_name).strip()
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        # Using setuptools here to sort out downloading the files
        py_prog = 'from setuptools.package_index import PackageIndex; ' \
                  'from pkg_resources import Requirement; ' \
                  'print PackageIndex().fetch_distribution(%r, %r, force_scan=True)' % (req, dest_dir)
        logger.debug(py_prog)
        # invoke python in subshell
        fetched = self.run('cd %s; %s -c "%s"' % (work_dir, self.python, py_prog), capture=True)
        print "Fetched %r" % fetched

    def post_setup(self):
        """ Upload the dependencies for pkglib so tagup
            can bootstrap itself as well as run tests on
            generated packages
        """
        # Lazy import here to get around pkg build circle
        from pkglib.setuptools.dependency import get_all_requirements

        work_dir = os.path.join(self.workspace, 'pkglib-deps')
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        with open(os.path.join(work_dir, '.pypirc'), 'wb') as rc_file:
            self.get_rc().write(rc_file)

        # XXX find a better way to pass in credentials
        new_env = copy.copy(dict(os.environ))
        new_env['HOME'] = work_dir
        for dist in get_all_requirements(['pkglib', 'pytest-cov']):
            # Quick hack to get the built eggs into the test PyPi instance.
            # We register with an empty package file then copy the files in manually
            name = dist.project_name
            # We may need pip and distribute if virtualenv installed old versions.
            # (should only occur when upgrading to new virtualenv).
            if name in ['pkglib', 'virtualenv', 'setuptools']:
                continue
            version = dist.version
            with open(os.path.join(work_dir, 'setup.py'), 'wb') as fp:
                fp.write(SETUP_TMPL % {'name': name, 'version': version})
            out = self.run('cd %s; %s setup.py register' % (work_dir, self.python), capture=True,
                           env=new_env)
            logger.debug(out)
            assert '200' in out
            self.upload_requirement(work_dir, dist.as_requirement())

    def save(self):
        raise NotImplemented()

    def restore(self):
        raise NotImplemented()


@contextmanager
def create_pkg(pypi, svn, name="acme.foo", metadata={}, dev=True):
    """ creates a pkg in a workspace as a context mgr
    """
    pkg_template = PkgTemplate(name=name, repo_base=svn.uri, metadata=metadata, dev=dev)

    workspace = pkg_template.workspace
    name = pkg_template.name
    python = pkg_template.python
    vcs_uri = pkg_template.vcs_uri

    print "%s: stored at %s" % (name, vcs_uri)

    pkg_template.create_pypirc(pypi.get_rc())
    pkg_template.run("svn import %s %s -m 'initial import'" % (name, pkg_template.vcs_uri),
        capture=True)
    # Now to check out to get subversion info
    pkg_template.run("mv %s imported_%s" % (name, name))
    pkg_template.run("svn co %s %s" % (pkg_template.vcs_uri, name))
    pkg_template.run("cd %s/%s/trunk; HOME=%s %s setup.py develop -i %s/simple/" % (
            workspace, name, workspace, python, pypi.uri), capture=True)
    pkg_template.run("cd %s/%s/trunk; HOME=%s %s setup.py bdist_egg register upload" % (
            workspace, name, workspace, python))
    yield pkg_template
    pkg_template.teardown


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
