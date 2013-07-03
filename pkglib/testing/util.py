"""     General util stuff.
"""
import os
import sys
import tempfile
import shutil
import subprocess
from subprocess import Popen, PIPE
from ConfigParser import ConfigParser
from pkg_resources import working_set
from contextlib import contextmanager, closing
import getpass

from path import path

from pkglib import CONFIG
from pkglib.testing.pytest import coverage

# ---------- Methods -------------------------#


def is_under_hudson():
    """ True if we're running in Hudson """
    tag = os.environ.get('BUILD_TAG', '')
    return tag.startswith('hudson') or tag.startswith('jenkins')


def get_base_tempdir():
    """ Returns an appropriate dir to pass into
        tempfile.mkdtemp(dir=xxx) or similar.
    """
    if is_under_hudson():
        return os.getenv('WORKSPACE')
    return None


@contextmanager
def chdir(dirname):
    """
    Context Manager to change to a dir then change back
    """
    try:
        here = os.getcwd()
    except OSError:
        here = None
    os.chdir(dirname)
    yield
    if here is not None:
        os.chdir(here)


@contextmanager
def set_env(*args, **kwargs):
    """Context Mgr to set an environment variable

    """
    def update_environment(env):
        for k, v in env.iteritems():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = str(v)

    # Backward compatibility with the old interface which only allowed to
    # update a single environment variable.
    new_values = dict([(args[0], args[1])]) if len(args) == 2 else {}
    new_values.update((k, v) for k, v in kwargs.iteritems())

    # Save variables that are going to be updated.
    saved_values = dict((k, os.environ.get(k)) for k in new_values.iterkeys())

    # Update variables to their temporary values
    update_environment(new_values)
    (yield)
    # Restore original environment
    update_environment(saved_values)


@contextmanager
def unset_env(env_var_skiplist):
    """Context Mgr to unset an environment variable temporarily."""
    def update_environment(env):
        os.environ.clear()
        os.environ.update(env)

    # Save variables that are going to be updated.
    saved_values = dict(os.environ)

    new_values = dict((k, v) for k, v in os.environ.iteritems()
                      if k not in env_var_skiplist)

    # Update variables to their temporary values
    update_environment(new_values)
    (yield)
    # Restore original environment
    update_environment(saved_values)


@contextmanager
def no_env(key):
    """
    Context Mgr to asserting no environment variable of the given name exists
    (sto enable the testing of the case where no env var of this name exists)
    """
    try:
        orig_value = os.environ[key]
        del os.environ[key]
        env_has_key = True
    except KeyError:
        env_has_key = False

    yield
    if env_has_key:
        os.environ[key] = orig_value
    else:
        # there shouldn't be a key in org state.. just check that there isn't
        try:
            del os.environ[key]
        except KeyError:
            pass


@contextmanager
def patch_getpass(username, password):
    """
    Patches the getuser() and getpass() functions in the getpass module
    replacing them with user specified values.

    """
    getuser_prev_callable = getpass.getuser
    getpass_prev_callable = getpass.getpass

    def _getpass(prompt='Password: ', stream=None):  # @UnusedVariable
        """A monkey patch for getpass that returns a specified password."""
        return password

    try:
        getpass.getuser = lambda: username
        getpass.getpass = _getpass
        yield
    finally:
        getpass.getuser = getuser_prev_callable
        getpass.getpass = getpass_prev_callable


@contextmanager
def patch_raw_input(user_input):
    """
    Patches the raw_input() built in function returning specified user input.

    """
    import __builtin__ as bi

    raw_input_prev_callable = bi.raw_input

    def _raw_input(msg=None):  # @UnusedVariable
        return user_input

    try:
        bi.raw_input = _raw_input
        yield
    finally:
        bi.raw_input = raw_input_prev_callable


def get_clean_python_env():
    """ Returns the shell environ stripped of its PYTHONPATH
    """
    env = dict(os.environ)
    if 'PYTHONPATH' in env:
        del(env['PYTHONPATH'])
    return env


def launch(cmd, **kwds):
    """Runs the command in a separate process and returns the lines of stdout
       and stderr as lists
    """
    if isinstance(cmd, basestring):
        cmd = [cmd]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, **kwds)
    return p.communicate()


class Shell(object):
    """Create a shell script which runs the command and optionally runs
       another program which returns to stdout/err retults to confirm success
       or failure
    """
    fname = None

    def __init__(self, func_commands, print_info=True, **kwds):
        if isinstance(func_commands, basestring):
            self.func_commands = [func_commands]
        else:
            self.func_commands = func_commands
        self.print_info = print_info
        self.kwds = kwds

    def __enter__(self):
        with closing(tempfile.NamedTemporaryFile('w', delete=False)) as f:
            self.cmd = f.name
            os.chmod(self.cmd, 0777)
            f.write('#!/bin/sh\n')

            for line in self.func_commands:
                f.write('%s\n' % line)

        self.out, self.err = launch(self.cmd, **self.kwds)

        return self

    def __exit__(self, ee, ei, tb):  # @UnusedVariable
        if os.path.isfile(self.cmd):
            os.remove(self.cmd)

    def print_io(self):
        def print_out_err(name, data):
            print name,
            if data.strip() == '':
                print ' <no data>'
            else:
                print
                for line in data.split('\n')[:-1]:
                    print line

        print '+++ Shell +++'
        print '--cmd:'
        for line in self.func_commands:
            print '* %s' % line
        print_out_err('--out', self.out)
        print_out_err('--err', self.err)
        print '=== Shell ==='


# ---------- Fixtures ----------------------- #


class Workspace(object):
    """
    Creates a temp workspace, cleans up on teardown.
    See pkglib.testing.pytest.util for an example usage.
    Can also be used as a context manager.

    Attributes
    ----------
    workspace : `path.path`
        Path to the workspace directory.
    dead: `bool`
        If false, will delete the workspace on teardown. Set this to true
        within a test run to stop the teardown.\
    debug: `bool`
        If set to True, will print more debug when running subprocess commands.
    delete: `bool`
        If set to False, will never delete the workspace on teardown
    """
    dead = False
    debug = False
    delete = True

    def __init__(self, workspace=None):
        print
        print "======================================================="
        if workspace is None:
            self.workspace = path(tempfile.mkdtemp(dir=get_base_tempdir()))
            print "pkglib.testing created workspace %s" % self.workspace
        else:
            self.workspace = workspace
            print "pkglib.testing using workspace %s" % self.workspace
            self.delete = False
        if 'DEBUG' in os.environ:
            self.debug = True
        print "======================================================="
        print

    def __enter__(self):
        return self

    def __exit__(self, errtype, value, traceback):  # @UnusedVariable
        self.teardown()

    def __del__(self):
        self.teardown()

    def run(self, cmd, capture=False, check_rc=True, cd=None, shell=True,
            **kwargs):
        """
        Run a command relative to a given directory, defaulting to the
        workspace root

        Parameters
        ----------
        cmd : `str`
            Command string.
        capture : `bool`
            Capture and return output
        check_rc : `bool`
            Assert return code is zero
        cd : `str`
            Path to chdir to, defaults to workspace root
        """
        if isinstance(cmd, str):
            cmd = [cmd]
            shell = True
        if not cd:
            cd = self.workspace
        with chdir(cd):
            #import sys; sys.stderr.write("chdir: %s run %s\n" % (cd, cmd))
            print "run: %s" % str(cmd)
            if capture:
                p = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, **kwargs)
            else:
                p = subprocess.Popen(cmd, shell=shell, **kwargs)
            (out, _) = p.communicate()
            if self.debug and capture:
                print "Stdout/stderr:"
                print out

            if check_rc:
                if not p.returncode == 0:
                    raise subprocess.CalledProcessError(p.returncode, out)
        return out

    def teardown(self):
        print 'self.delete:', self.delete
        print 'self.dead:', self.dead
        print 'is_under_hudson?:', is_under_hudson()
        if not self.delete:
            return
        # Don't delete the evidence if we're running in Hudson
        if self.dead and not is_under_hudson():
            print
            print "======================================================="
            print "pkglib.testing deleting workspace %s" % self.workspace
            print "======================================================="
            print
            shutil.rmtree(self.workspace)


# enumeration of options of package types to describe the sub-types of those installed


##--- for testimg ---


class TmpVirtualEnv(Workspace):
    """
    Creates a virtualenv in a temporary workspace, cleans up on exit.

    Attributes
    ----------
    python : `str`
        path to the python exe
    virtualenv : `str`
        path to the virtualenv base dir
    env : 'list'
        environment variables used in creation of virtualenv

    """

    def __init__(self, env=None):
        Workspace.__init__(self)
        self.virtualenv = self.workspace / '.env'
        self.python = self.virtualenv / 'bin' / 'python'
        self.easy_install = self.virtualenv / "bin" / "easy_install"

        if env is None:
            self.env = dict(os.environ)
        else:
            # ensure we take a copy just in case there's some modification
            self.env = dict(env)

        self.env['VIRTUAL_ENV'] = self.virtualenv
        if 'PYTHONPATH' in self.env:
            del(self.env['PYTHONPATH'])
        self.run('%s %s --distribute' % (CONFIG.virtualenv_executable,
                                         self.virtualenv))
        #self.install_package('yolk', installer='easy_install')

    def run(self, *args, **kwargs):
        """
        Add our cleaned shell environment into any subprocess execution
        """
        if 'env' not in kwargs:
            kwargs['env'] = self.env
        return super(TmpVirtualEnv, self).run(*args, **kwargs)

    def run_with_coverage(self, *args, **kwargs):
        """
        Run a python script using coverage, run within this virtualenv.
        Assumes the coverage module is already installed.

        Parameters
        ----------
        args:
            Args passed into `pkglib.testing.pytest.coverage.run_with_coverage`
        kwargs:
            Keyword arguments to pass to
            `pkglib.testing.pytest.coverage.run_with_coverage`
        """
        if 'env' not in kwargs:
            kwargs['env'] = self.env
        return coverage.run_with_coverage(
              *args, coverage='%s/bin/coverage' % self.virtualenv, **kwargs)

    def install_package(self, pkg_name, installer='pyinstall',
                        build_egg=False):
        """
        Install a given package name. If it's already setup in the
        test runtime environment, it will use that.

        Parameters
        ----------
        build_egg:  `bool`
            Only used when the package is installed as a source checkout,
            otherwise it runs the installer to get it from PyPI
            True: builds an egg and installs it
            False: Runs 'python setup.py develop'
        """
        cmd = []
        installed = [p for p in working_set if p.project_name == pkg_name]
        if not installed or installed[0].location.endswith('.egg'):
            installer = os.path.join(self.virtualenv, 'bin', installer)
            if not self.debug:
                installer += ' -q'
            # Note we're running this as 'python easy_install foobar', instead 
            # of 'easy_install foobar'
            # This is to circumvent #! line length limits :(
            cmd.append('%s %s %s' % (self.python, installer, pkg_name))
        else:
            pkg = installed[0]
            d = {'python': self.python,
                 'easy_install': self.easy_install,
                 'src_dir': pkg.location,
                 'name': pkg.project_name,
                 'version': pkg.version,
                 'pyversion': '%d.%d' % sys.version_info[:2],
                 }

            d['egg_file'] = (path(pkg.location) / 'dist' /
                             ('%(name)s-%(version)s-py%(pyversion)s.egg' % d))

            if build_egg:
                cmd += ['cd %(src_dir)s' % d,
                        '%(python)s setup.py -q bdist_egg' % d]

            # See if there's an egg available already.
            if d['egg_file'].isfile():
                cmd += ['%(python)s %(easy_install)s %(egg_file)s' % d]

            else:
                cmd += ['cd %(src_dir)s' % d,
                        '%(python)s setup.py -q develop' % d]

        self.run(';'.join(cmd), capture=True)

    def installed_packages(self, package_type=None):
        """
        Return a package dict with
            key = package name, value = version (or '')
        """
        if package_type is None:
            package_type = PackageEntry.ANY
        elif package_type not in PackageEntry.PACKAGE_TYPES:
            raise ValueError('invalid package_type parameter ({})'
                             .format(package_type))

        res = {}
        code = "from pkg_resources import working_set\n"\
               "for i in working_set: print i.project_name, i.version, i.location"
        lines = (self.run('%s -c "%s"' % (self.python, code), capture=True)
                 .split('\n'))
        for line in [i.strip() for i in lines if i.strip()]:
            name, version, location = line.split()
            res[name] = PackageEntry(name, version, location)
        return res

    def popen(self, cmd, **kwds):
        kwds = dict(kwds)
        kwds.setdefault("stdout", subprocess.PIPE)
        return subprocess.Popen(cmd, **kwds).stdout

    def dependencies(self, package_name, package_type=None):  # @UnusedVariable
        """
        Find the dependencies of a given package.

        Parameters
        ----------
        package_name: `str`
            Name of package
        package_type: `str`
            Filter results on package type

        Returns
        --------
        dependencies: `dict`
            Key is name, value is PackageEntries
        """
        if package_type is None:
            package_type = PackageEntry.ANY
        elif package_type not in (PackageEntry.DEV, PackageEntry.REL):
            raise ValueError('invalid package_type parameter for dependencies '
                             '({})'.format(package_type))

        res = {}
        code = "from pkglib.setuptools.dependency import get_all_requirements; " \
               "for i in get_all_requirements(['%s']): " \
               "  print i.project_name, i.version, i.location"
        lines = self.run('%s -c "%s"' % (self.python, code), capture=True).split('\n')
        for line in [i.strip() for i in lines if i.strip()]:
            name, version, location = line.split()
            entry = PackageEntry(name, version, location)
            if entry.match(package_type):
                res[name] = entry
        return res


class SVNRepo(Workspace):
    """
    Creates an empty SVN repository in a temporary workspace.
    Cleans up on exit.

    Attributes
    ----------
    uri : `str`
        repository base uri
    """
    def __init__(self):
        super(SVNRepo, self).__init__()
        self.run('svnadmin create .', capture=True)
        self.uri = "file://%s" % self.workspace


class PkgTemplate(TmpVirtualEnv):
    """
    Creates a new package from the package templates in a temporary workspace.
    Cleans up on exit.

    Attributes
    ----------
    vcs_uri : `str`
        path to a local repository for this package
    trunk_dir : `path.path`
        path to the trunk package directory
    """

    def __init__(self, repo_base='http://svn_foo', name='acme.foo', metadata={}, dev=True,
                 template_type="pkglib_project", paster_args='', **kwargs):
        """
        Parameters
        ----------
        repo_base : `str`
            repository base uri
        name : `str`
            package name
        metadata : `dict`
            override any metadata
        dev : `bool`
            set dev marker (ie, pkg-version.dev1)

        kwargs: any other config options to set
        """
        TmpVirtualEnv.__init__(self)
        self.name = name

        # Install pkgutils
        self.install_package('pkglib', installer='easy_install')

        # Create template
        self.run('{virtualenv}/bin/paster create -t {template_type} {name} '
                 '--no-interactive {paster_args}'.format(virtualenv=self.virtualenv,
                                                         name=self.name,
                                                         template_type=template_type,
                                                         paster_args=paster_args), capture=True)

        self.vcs_uri = '%s/%s' % (repo_base, self.name)
        self.trunk_dir = self.workspace / self.name / 'trunk'

        # Update setup.cfg
        c = ConfigParser()
        cfg = self.trunk_dir / 'setup.cfg'
        c.read(cfg)
        _metadata = dict(
            url=self.vcs_uri,
            author='test',
            author_email='test@test.example',
        )
        _metadata.update(metadata)
        for k, v in _metadata.items():
            c.set('metadata', k, v)

        if not dev:
            c.set('egg_info', 'tag_build', '')

        for section, vals in kwargs.items():
            if not c.has_section(section):
                c.add_section(section)
            for k, v in vals.items():
                c.set(section, k, v)

        with open(cfg, 'wb') as cfg_file:
            c.write(cfg_file)

    def create_pypirc(self, config):
        """
        Create a .pypirc file in the workspace

        Parameters
        ----------
        config : `ConfigParser.ConfigParser`
            config instance
        """
        with open(os.path.join(self.workspace, '.pypirc'), 'wb') as rc_file:
            config.write(rc_file)


class PackageEntry(object):
    # TODO: base this off of Distribution or similar
    PACKAGE_TYPES = (ANY, DEV, SRC, REL) = ('ANY', 'DEV', 'SRC', 'REL')

    def __init__(self, name, version, source_path=None):
        self.name = name
        self.version = version
        self.source_path = source_path

    @property
    def issrc(self):
        return ("dev" in self.version and
                self.source_path is not None and
                not self.source_path.endswith(".egg"))

    @property
    def isrel(self):
        return not self.isdev

    @property
    def isdev(self):
        return ('dev' in self.version and
                (not self.source_path or self.source_path.endswith(".egg")))

    def match(self, package_type):
        if package_type is self.ANY:
                return True
        elif package_type is self.REL:
            if self.isrel:
                return True
        elif package_type is self.DEV:
            if self.isdev:
                return True
        elif package_type is self.SRC:
            if self.issrc:
                return True
        return False
