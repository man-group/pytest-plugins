""" Python virtual environment fixtures
"""
import os
import sys
from distutils import sysconfig

from pytest import yield_fixture
from pkg_resources import working_set
try:
    from path import Path
except ImportError:
    from path import path as Path

from pytest_shutil.workspace import Workspace
from pytest_shutil import run, cmdline
from pytest_fixture_config import Config, yield_requires_config


class FixtureConfig(Config):
    __slots__ = ('virtualenv_executable')

# Default values for system resource locations - patch this to change defaults
DEFAULT_VIRTUALENV_FIXTURE_EXECUTABLE = (cmdline.which('virtualenv') + ['virtualenv'])[0]

CONFIG = FixtureConfig(
    virtualenv_executable=os.getenv('VIRTUALENV_FIXTURE_EXECUTABLE', DEFAULT_VIRTUALENV_FIXTURE_EXECUTABLE),
)


@yield_requires_config(CONFIG, ['virtualenv_executable'])
@yield_fixture(scope='function')
def virtualenv():
    """ Function-scoped virtualenv in a temporary workspace.

        Methods
        -------
        run()                : run a command using this virtualenv's shell environment
        run_with_coverage()  : run a command in this virtualenv, collecting coverage
        install_package()    : install a package in this virtualenv
        installed_packages() : return a dict of installed packages

        Attributes
        ----------
        virtualenv (`path.path`)    : Path to this virtualenv's base directory
        python (`path.path`)        : Path to this virtualenv's Python executable
        easy_install (`path.path`)  : Path to this virtualenv's easy_install executable
        .. also inherits all attributes from the `workspace` fixture
    """
    with VirtualEnv() as venv:
        yield venv


class PackageEntry(object):
    # TODO: base this off of setuptools Distribution class or something not home-grown
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


class VirtualEnv(Workspace):
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
    # TODO: update to use pip, remove distribute
    def __init__(self, env=None, workspace=None, name='.env', python=None, args=None):
        Workspace.__init__(self, workspace)
        self.virtualenv = self.workspace / name
        self.args = args or []
        if sys.platform == 'win32':
            # In virtualenv on windows "Scripts" folder is used instead of "bin".
            self.python = self.virtualenv / 'Scripts' / 'python.exe'
            self.easy_install = self.virtualenv / 'Scripts' / 'easy_install.exe'
            self.coverage = self.virtualenv / 'Scripts' / 'coverage.exe'
        else:
            self.python = self.virtualenv / 'bin' / 'python'
            self.easy_install = self.virtualenv / "bin" / "easy_install"
            self.coverage = self.virtualenv / 'bin' / 'coverage'

        if env is None:
            self.env = dict(os.environ)
        else:
            self.env = dict(env)  # ensure we take a copy just in case there's some modification

        self.env['VIRTUAL_ENV'] = str(self.virtualenv)

        self.env['PATH'] = str(self.python.dirname()) + ((os.path.pathsep + self.env["PATH"])
                                                         if "PATH" in self.env else "")
        if 'PYTHONPATH' in self.env:
            del(self.env['PYTHONPATH'])

        self.virtualenv_cmd = CONFIG.virtualenv_executable
        cmd = [self.virtualenv_cmd,
               '-p', python or cmdline.get_real_python_executable()
               ]
        cmd.extend(self.args)
        cmd.append(str(self.virtualenv))
        self.run(cmd)

    def run(self, args, **kwargs):
        """
        Add our cleaned shell environment into any subprocess execution
        """
        if 'env' not in kwargs:
            kwargs['env'] = self.env
        return super(VirtualEnv, self).run(args, **kwargs)

    def run_with_coverage(self, *args, **kwargs):
        """
        Run a python script using coverage, run within this virtualenv.
        Assumes the coverage module is already installed.

        Parameters
        ----------
        args:
            Args passed into `pytest_shutil.run.run_with_coverage`
        kwargs:
            Keyword arguments to pass to `pytest_shutil.run.run_with_coverage`
        """
        if 'env' not in kwargs:
            kwargs['env'] = self.env
        coverage = [str(self.python), str(self.coverage)]
        return run.run_with_coverage(*args, coverage=coverage, **kwargs)

    def install_package(self, pkg_name, installer='easy_install', build_egg=None):
        """
        Install a given package name. If it's already setup in the
        test runtime environment, it will use that.
        :param build_egg:  `bool`
            Only used when the package is installed as a source checkout, otherwise it
            runs the installer to get it from PyPI.
            True: builds an egg and installs it
            False: Runs 'python setup.py develop'
            None (default): installs the egg if available in dist/, otherwise develops it
        """
        installed = [p for p in working_set if p.project_name == pkg_name]
        if not installed or installed[0].location.endswith('.egg'):
            if sys.platform == 'win32':
                # In virtualenv on windows "Scripts" folder is used instead of "bin".
                installer = str(self.virtualenv / 'Scripts' / installer + '.exe')
            else:
                installer = str(self.virtualenv / 'bin' / installer)
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

            d['egg_file'] = Path(pkg.location) / 'dist' / ('%(name)s-%(version)s-py%(pyversion)s.egg' % d)
            if build_egg and not d['egg_file'].isfile():
                self.run('cd %(src_dir)s; %(python)s setup.py -q bdist_egg' % d, capture=True)

            if build_egg or (build_egg is None and d['egg_file'].isfile()):
                cmd = '%(python)s %(easy_install)s %(egg_file)s' % d
            else:
                cmd = 'cd %(src_dir)s; %(python)s setup.py -q develop' % d

        self.run(cmd, capture=False)

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
        lines = self.run([self.python, "-c", code], capture=True).split('\n')
        for line in [i.strip() for i in lines if i.strip()]:
            name, version, location = line.split()
            res[name] = PackageEntry(name, version, location)
        return res
