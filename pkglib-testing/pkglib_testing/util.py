"""General utility stuff.
"""
import getpass
import imp
import os
import sys
import tempfile
import shutil
import subprocess
from functools import update_wrapper
import inspect
import textwrap

from mock import patch
from path import path

from contextlib import contextmanager, closing
from subprocess import Popen, PIPE
from distutils import sysconfig
import execnet

from pkglib.six import string_types
from pkglib.six.moves import builtins, configparser, cPickle  # @UnresolvedImport
from pkglib.six.moves import input as raw_input
from pkglib.six.moves import ExitStack  # @UnresolvedImport

from pkg_resources import working_set

from pkglib_testing import CONFIG
from pkglib_util import cmdline

from .pytest import coverage as cov

# ---------- Methods -------------------------#


def get_base_tempdir():
    """ Returns an appropriate dir to pass into
        tempfile.mkdtemp(dir=xxx) or similar.
    """
    return os.getenv('WORKSPACE')


# TODO: merge with cmdline
@contextmanager
def set_env(*args, **kwargs):
    """Context Mgr to set an environment variable

    """
    def update_environment(env):
        for k, v in env.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = str(v)

    # Backward compatibility with the old interface which only allowed to
    # update a single environment variable.
    new_values = dict([(args[0], args[1])]) if len(args) == 2 else {}
    new_values.update((k, v) for k, v in kwargs.items())

    # Save variables that are going to be updated.
    saved_values = dict((k, os.environ.get(k)) for k in new_values.keys())

    # Update variables to their temporary values
    try:
        update_environment(new_values)
        yield
    finally:
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

    new_values = dict((k, v) for k, v in os.environ.items() if k not in env_var_skiplist)

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
    _raw_input_func_name = raw_input.__name__  # @UndefinedVariable
    raw_input_prev_callable = getattr(builtins, _raw_input_func_name)

    def _raw_input(msg=None):  # @UnusedVariable
        return user_input

    try:
        setattr(builtins, _raw_input_func_name, _raw_input)
        yield
    finally:
        setattr(builtins, _raw_input_func_name, raw_input_prev_callable)


def get_clean_python_env():
    """ Returns the shell environ stripped of its PYTHONPATH
    """
    env = dict(os.environ)
    if 'PYTHONPATH' in env:
        del(env['PYTHONPATH'])
    return env


def launch(cmd, **kwds):
    """Runs the command in a separate process and returns the lines of stdout and stderr
    as lists
    """
    if isinstance(cmd, string_types):
        cmd = [cmd]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, **kwds)
    out, err = p.communicate()

    # FIXME: can decoding below break on some unorthodox output?
    if out is not None and not isinstance(out, string_types):
        out = out.decode('utf-8')

    if err is not None and not isinstance(err, string_types):
        err = err.decode('utf-8')

    return (out, err)


def get_real_python_executable():
    real_prefix = getattr(sys, "real_prefix", None)
    if not real_prefix:
        return sys.executable

    executable_name = os.path.basename(sys.executable)
    bindir = os.path.join(real_prefix, "bin")
    if not os.path.isdir(bindir):
        print("Unable to access bin directory of original Python "
              "installation at: %s" % bindir)
        return sys.executable

    executable = os.path.join(bindir, executable_name)
    if not os.path.exists(executable):
        executable = None
        for f in os.listdir(bindir):
            if not f.endswith("ython"):
                continue

            f = os.path.join(bindir, f)
            if os.path.isfile(f):
                executable = f
                break

        if not executable:
            print("Unable to locate a valid Python executable of original "
                  "Python installation at: %s" % bindir)
            executable = sys.executable

    return executable


def create_package_from_template(venv, name, template="pkglib_project", paster_args="", metadata=None,
                                 repo_base="http://test_repo_base", dev=True, install_requires=None, **kwargs):
    metadata = {} if metadata is None else dict(metadata)
    if '-' in name:
        pkg_name, _, version = name.rpartition('-')
        pkg_name = metadata.setdefault('name', pkg_name)
        version = metadata.setdefault('version', version)
        dev = (version.rpartition('.')[2] == 'dev1')
        if dev:
            metadata['version'] = version = version.rpartition('.')[0]
    else:
        pkg_name = metadata.setdefault('name', name)
        version = metadata.setdefault('version', '1.0.0.dev1' if dev else '1.0.0')
    if install_requires is not None:
        if not isinstance(install_requires, str):
            install_requires = '\n'.join(install_requires)
        metadata['install_requires'] = install_requires

    venv.run('{python} {virtualenv}/bin/pymkproject -t {template_type} {name} '
             '--no-interactive {paster_args}'.format(python=venv.python,
                                                     virtualenv=venv.virtualenv,
                                                     name=pkg_name,
                                                     template_type=template,
                                                     paster_args=paster_args), capture=True)
    if name != pkg_name:
        os.rename(venv.workspace / pkg_name, venv.workspace / name)
    vcs_uri = '%s/%s' % (repo_base, pkg_name)
    trunk_dir = venv.workspace / name / 'trunk'
    update_setup_cfg(trunk_dir / 'setup.cfg', vcs_uri=vcs_uri, metadata=metadata, dev=dev, **kwargs)
    return vcs_uri, trunk_dir


def update_setup_cfg(cfg, vcs_uri, metadata={}, dev=True, **kwargs):
    # Update setup.cfg
    c = configparser.ConfigParser()
    c.read(cfg)
    _metadata = dict(
        url=vcs_uri,
        author='test',
        author_email='test@test.example',
    )
    _metadata.update(metadata)
    for k, v in _metadata.items():
        c.set('metadata', k, v)

    if not dev:
        c.remove_option('egg_info', 'tag_build')
        c.remove_option('egg_info', 'tag_svn_revision')

    for section, vals in kwargs.items():
        if not c.has_section(section):
            c.add_section(section)
        for k, v in vals.items():
            c.set(section, k, v)

    with open(cfg, 'w') as cfg_file:
        c.write(cfg_file)


class Shell(object):
    """Create a shell script which runs the command and optionally runs
    another program which returns to stdout/err retults to confirm success or failure
    """
    fname = None

    def __init__(self, func_commands, print_info=True, **kwds):
        if isinstance(func_commands, string_types):
            self.func_commands = [func_commands]
        else:
            self.func_commands = func_commands
        self.print_info = print_info
        self.kwds = kwds

    def __enter__(self):
        with closing(tempfile.NamedTemporaryFile('w', delete=False)) as f:
            self.cmd = f.name
            os.chmod(self.cmd, 0o777)
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
            print(name)
            if data.strip() == '':
                print(' <no data>')
            else:
                print()
                for line in data.split('\n')[:-1]:
                    print(line)

        print('+++ Shell +++')
        print('--cmd:')
        for line in self.func_commands:
            print('* %s' % line)
        print_out_err('--out', self.out)
        print_out_err('--err', self.err)
        print('=== Shell ===')


# ---------- Fixtures ----------------------- #


class Workspace(object):
    """
    Creates a temp workspace, cleans up on teardown.
    See pkglib_testing.pytest.util for an example usage.
    Can also be used as a context manager.

    Attributes
    ----------
    workspace : `path.path`
        Path to the workspace directory.
    debug: `bool`
        If set to True, will print more debug when running subprocess commands.
    delete: `bool`
        If True, will always delete the workspace on teardown; if None, delete
        the workspace unless teardown occurs via an exception; if False, never
        delete the workspace on teardown.
    """
    debug = False
    delete = True

    def __init__(self, workspace=None, delete=None):
        self.delete = delete

        print("")
        print("=======================================================")
        if workspace is None:
            self.workspace = path(tempfile.mkdtemp(dir=get_base_tempdir()))
            print("pkglib_testing created workspace %s" % self.workspace)
        else:
            self.workspace = workspace
            print("pkglib_testing using workspace %s" % self.workspace)
        if 'DEBUG' in os.environ:
            self.debug = True
        if self.delete is not False:
            print("This workspace will delete itself on teardown")
        print("=======================================================")
        print("")

    def __enter__(self):
        return self

    def __exit__(self, errtype, value, traceback):  # @UnusedVariable
        if self.delete is None:
            self.delete = (errtype is None)
        self.teardown()

    def __del__(self):
        self.teardown()

    def run(self, cmd, capture=False, check_rc=True, cd=None, shell=True, **kwargs):
        """
        Run a command relative to a given directory, defaulting to the workspace root

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
        with cmdline.chdir(cd):
            print("run: %s" % str(cmd))
            if capture:
                p = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
            else:
                p = subprocess.Popen(cmd, shell=shell, **kwargs)
            (out, _) = p.communicate()

            if out is not None and not isinstance(out, string_types):
                out = out.decode('utf-8')

            if self.debug and capture:
                print("Stdout/stderr:")
                print(out)

            if check_rc and p.returncode != 0:
                err = subprocess.CalledProcessError(p.returncode, cmd)
                err.output = out
                if capture and not self.debug:
                    print("Stdout/stderr:")
                    print(out)
                raise err

        return out

    def teardown(self):
        if not self.delete:
            return
        if os.path.isdir(self.workspace):
            print("")
            print("=======================================================")
            print("pkglib_testing deleting workspace %s" % self.workspace)
            print("=======================================================")
            print("")
            shutil.rmtree(self.workspace)

    def create_pypirc(self, config):
        """
        Create a .pypirc file in the workspace

        Parameters
        ----------
        config : `ConfigParser.ConfigParser`
            config instance
        """
        f = os.path.join(self.workspace, '.pypirc')
        mode = os.O_WRONLY | os.O_CREAT
        perm = 0o600

        with os.fdopen(os.open(f, mode, perm), 'wt') as rc_file:
            config.write(rc_file)


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

    def __init__(self, env=None, workspace=None, name='.env', python=None):
        Workspace.__init__(self, workspace)
        self.virtualenv = self.workspace / name
        self.python = self.virtualenv / 'bin' / 'python'
        self.easy_install = self.virtualenv / "bin" / "easy_install"

        if env is None:
            self.env = dict(os.environ)
        else:
            self.env = dict(env)  # ensure we take a copy just in case there's some modification

        self.env['VIRTUAL_ENV'] = self.virtualenv
        self.env['PATH'] = os.path.dirname(self.python) + ((os.path.pathsep + self.env["PATH"])
                                                           if "PATH" in self.env else "")
        if 'PYTHONPATH' in self.env:
            del(self.env['PYTHONPATH'])

        virtualenv_cmd = CONFIG.virtualenv_executable
        self.run('%s -p %s %s --distribute' % (virtualenv_cmd,
                                               python or get_real_python_executable(),
                                               self.virtualenv))
        self.install_package('six', installer='easy_install')

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
            Args passed into `pkglib_testing.pytest.coverage.run_with_coverage`
        kwargs:
            Keyword arguments to pass to `pkglib_testing.pytest.coverage.run_with_coverage`
        """
        if 'env' not in kwargs:
            kwargs['env'] = self.env
        coverage = [self.python, '%s/bin/coverage' % self.virtualenv]
        return cov.run_with_coverage(*args, coverage=coverage, **kwargs)

    def install_package(self, pkg_name, installer='pyinstall', build_egg=None):
        """
        Install a given package name. If it's already setup in the
        test runtime environment, it will use that.
        :param build_egg:  `bool`
            Only used when the package is installed as a source checkout, otherwise it
            runs the installer to get it from AHLPyPI
            True: builds an egg and installs it
            False: Runs 'python setup.py develop'
            None (default): installs the egg if available in dist/, otherwise develops it
        """
        installed = [p for p in working_set if p.project_name == pkg_name]
        if not installed or installed[0].location.endswith('.egg'):
            installer = os.path.join(self.virtualenv, 'bin', installer)
            if not self.debug:
                installer += ' -q'
            # Note we're running this as 'python easy_install foobar', instead of 'easy_install foobar'
            # This is to circumvent #! line length limits :(
            cmd = '%s %s %s' % (self.python, installer, pkg_name)
        else:
            pkg = installed[0]
            d = {'python': self.python,
                 'easy_install': self.easy_install,
                 'src_dir': pkg.location,
                 'name': pkg.project_name,
                 'version': pkg.version,
                 'pyversion': sysconfig.get_python_version(),
                 }

            d['egg_file'] = path(pkg.location) / 'dist' / ('%(name)s-%(version)s-py%(pyversion)s.egg' % d)
            if build_egg and not d['egg_file'].isfile():
                self.run('cd %(src_dir)s; %(python)s setup.py -q bdist_egg' % d, capture=True)

            if build_egg or (build_egg is None and d['egg_file'].isfile()):
                cmd = '%(python)s %(easy_install)s %(egg_file)s' % d
            else:
                cmd = 'cd %(src_dir)s; %(python)s setup.py -q develop' % d

        self.run(cmd, capture=True)

    def installed_packages(self, package_type=None):
        """
        Return a package dict with
            key = package name, value = version (or '')
        """
        if package_type is None:
            package_type = PackageEntry.ANY
        elif package_type not in PackageEntry.PACKAGE_TYPES:
            raise ValueError('invalid package_type parameter (%s)' % str(package_type))

        res = {}
        code = "from pkg_resources import working_set\n"\
               "for i in working_set: print(i.project_name + ' ' + i.version + ' ' + i.location)"
        lines = self.run('%s -c "%s"' % (self.python, code), capture=True).split('\n')
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
            raise ValueError('invalid package_type parameter for dependencies (%s)' % str(package_type))

        res = {}
        code = "from pkglib.setuptools.dependency import get_all_requirements; " \
               "for i in get_all_requirements(['%s']): " \
               "  print(i.project_name + ' ' + i.version + ' ' + i.location)"
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

    def __init__(self, name='acme.foo-1.0.dev1', **kwargs):
        """
        Parameters
        ----------
        name : `str`
            package name

        kwargs: any other config options to set
        """
        TmpVirtualEnv.__init__(self)
        self.name = name

        # Install pkglib
        self.install_package('pkglib', installer='easy_install', build_egg=True)

        self.vcs_uri, self.trunk_dir = create_package_from_template(self, name, **kwargs)


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


def run_as_main(module, argv=[]):
    where = os.path.dirname(module.__file__)
    filename = os.path.basename(module.__file__)
    filename = os.path.splitext(filename)[0] + ".py"

    with patch("sys.argv", new=argv):
        imp.load_source('__main__', os.path.join(where, filename))


def _evaluate_fn_source(src, *args, **kwargs):
    locals_ = {}
    eval(compile(src, '<string>', 'single'), {}, locals_)
    fn = next(iter(locals_.values()))
    if isinstance(fn, staticmethod):
        fn = fn.__get__(None, object)
    return fn(*args, **kwargs)


def _invoke_method(obj, name, *args, **kwargs):
    return getattr(obj, name)(*args, **kwargs)


def _find_class_from_staticmethod(fn):
    for _, cls in inspect.getmembers(sys.modules[fn.__module__], inspect.isclass):
        for name, member in inspect.getmembers(cls):
            if member is fn or (isinstance(member, staticmethod) and member.__get__(None, object) is fn):
                return cls, name
    return None, None


def _make_pickleable(fn):
    # return a pickleable function followed by a tuple of initial arguments
    # could use partial but this is more efficient
    try:
        cPickle.dumps(fn, protocol=0)
    except TypeError:
        pass
    else:
        return fn, ()
    if inspect.ismethod(fn):
        name, self_ = fn.__name__, fn.__self__
        if self_ is None:  # Python 2 unbound method
            self_ = fn.im_class
        return _invoke_method, (self_, name)
    elif inspect.isfunction(fn) and fn.__module__ in sys.modules:
        cls, name = _find_class_from_staticmethod(fn)
        if (cls, name) != (None, None):
            try:
                cPickle.dumps((cls, name), protocol=0)
            except cPickle.PicklingError:
                pass
            else:
                return _invoke_method, (cls, name)
    # Fall back to sending the source code
    return _evaluate_fn_source, (textwrap.dedent(inspect.getsource(fn)),)


def _run_in_subprocess_redirect_stdout(fd):
    import os  # @Reimport
    import sys  # @Reimport
    sys.stdout.close()
    os.dup2(fd, 1)
    os.close(fd)
    sys.stdout = os.fdopen(1, 'w', 1)


def _run_in_subprocess_remote_fn(channel):
    from pkglib.six.moves import cPickle  # @UnresolvedImport @Reimport # NOQA
    fn, args, kwargs = cPickle.loads(channel.receive(-1))
    channel.send(cPickle.dumps(fn(*args, **kwargs), protocol=0))


def run_in_subprocess(fn, python=sys.executable, cd=None, timeout=(-1)):
    """Wrap a function to run in a subprocess.  The function must be
    pickleable or otherwise must be totally self-contained; it must not
    reference a closure or any globals.  It can also be the source of a
    function (def fn(...): ...).

    Raises execnet.RemoteError on exception.
    """
    pkl_fn, preargs = (_evaluate_fn_source, (fn,)) if isinstance(fn, str) else _make_pickleable(fn)
    spec = '//'.join(filter(None, ['popen', 'python=' + python, 'chdir=' + cd if cd else None]))

    def inner(*args, **kwargs):
        # execnet sends stdout to /dev/null :(
        fix_stdout = sys.version_info < (3, 0, 0)  # Python 3 passes close_fds=True to subprocess.Popen
        with ExitStack() as stack:
            with ExitStack() as stack2:
                if fix_stdout:
                    fd = os.dup(1)
                    stack2.callback(os.close, fd)
                gw = execnet.makegateway(spec)  # @UndefinedVariable
                stack.callback(gw.exit)
            if fix_stdout:
                with closing(gw.remote_exec(_run_in_subprocess_remote_fn)) as chan:
                    chan.send(cPickle.dumps((_run_in_subprocess_redirect_stdout, (fd,), {}), protocol=0))
                    chan.receive(-1)
            with closing(gw.remote_exec(_run_in_subprocess_remote_fn)) as chan:
                payload = (pkl_fn, tuple(i for t in (preargs, args) for i in t), kwargs)
                chan.send(cPickle.dumps(payload, protocol=0))
                return cPickle.loads(chan.receive(timeout))
    return inner if isinstance(fn, str) else update_wrapper(inner, fn)
