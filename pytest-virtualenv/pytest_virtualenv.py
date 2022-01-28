""" Python virtual environment fixtures
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
from enum import Enum

import importlib_metadata as metadata
import pkg_resources
from pytest import yield_fixture

from pytest_shutil.workspace import Workspace
from pytest_shutil import run, cmdline
from pytest_fixture_config import Config, yield_requires_config


class PackageVersion(Enum):
    LATEST = 1
    CURRENT = 2

class FixtureConfig(Config):
    __slots__ = ('virtualenv_executable')

# Default values for system resource locations - patch this to change defaults
# Can be a string or list of them
DEFAULT_VIRTUALENV_FIXTURE_EXECUTABLE = [sys.executable, '-m', 'virtualenv']

CONFIG = FixtureConfig(
    virtualenv_executable=os.getenv('VIRTUALENV_FIXTURE_EXECUTABLE', DEFAULT_VIRTUALENV_FIXTURE_EXECUTABLE),
)


@yield_fixture(scope='function')
@yield_requires_config(CONFIG, ['virtualenv_executable'])
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
        pip (`path.path`)           : Path to this virtualenv's pip executable
        .. also inherits all attributes from the `workspace` fixture
    """
    venv = VirtualEnv()
    yield venv
    venv.teardown()


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
    delete_workspace: `None or bool`
        If True then the workspace will be deleted
        If False then the workspace will be kept
        If None (default) then the workspace will be deleted if workspace is also None, but it will be kept otherwise
    """
    # TODO: update to use pip, remove distribute
    def __init__(self, env=None, workspace=None, name='.env', python=None, args=None, delete_workspace=None):
        if delete_workspace is None:
            delete_workspace = workspace is None
        Workspace.__init__(self, workspace, delete_workspace)
        self.virtualenv = self.workspace / name
        self.args = args or []
        if sys.platform == 'win32':
            # In virtualenv on windows "Scripts" folder is used instead of "bin".
            self.python = self.virtualenv / 'Scripts' / 'python.exe'
            self.pip = self.virtualenv / 'Scripts' / 'pip.exe'
            self.coverage = self.virtualenv / 'Scripts' / 'coverage.exe'
        else:
            self.python = self.virtualenv / 'bin' / 'python'
            self.pip = self.virtualenv / "bin" / "pip"
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
        if isinstance(self.virtualenv_cmd, str):
            cmd = [self.virtualenv_cmd]
        else:
            cmd = list(self.virtualenv_cmd)
        cmd.extend(['-p', python or cmdline.get_real_python_executable()])
        cmd.extend(self.args)
        cmd.append(str(self.virtualenv))
        self.run(cmd)
        self._importlib_metadata_installed = False

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

    def install_package(self, pkg_name, version=PackageVersion.LATEST, installer="pip", installer_command="install"):
        """
        Install a given package name. If it's already setup in the
        test runtime environment, it will use that.
        :param pkg_name: `str`
            Name of the package to be installed
        :param version: `str` or `PackageVersion`
            If PackageVersion.LATEST then installs the latest version of the package from upstream
            If PackageVersion.CURRENT then installs the same version that's installed in the current virtual environment
                                      that's running the tests If the package is an egg-link, then copy it over. If the
                                      package is not in the parent, then installs the latest version
            If the value is a string, then it will be used as the version to install
        :param installer: `str`
            The installer used to install packages, `pip` by default
        `param installer_command: `str`
            The command passed to the installed, `install` by default. So the resulting default install command is
            `<venv>/Scripts/pip.exe install` on windows and `<venv>/bin/pip install` elsewhere
        """
        if sys.platform == 'win32':
            # In virtualenv on windows "Scripts" folder is used instead of "bin".
            installer = str(self.virtualenv / 'Scripts' / installer + '.exe')
        else:
            installer = str(self.virtualenv / 'bin' / installer)
        if not self.debug:
            installer += ' -q'

        if version == PackageVersion.LATEST:
            self.run(
                "{python} {installer} {installer_command} {spec}".format(
                    python=self.python, installer=installer, installer_command=installer_command, spec=pkg_name
                )
            )
        elif version == PackageVersion.CURRENT:
            dist = next(
                iter([dist for dist in metadata.distributions() if _normalize(dist.name) == _normalize(pkg_name)]), None
            )
            if dist:
                egg_link = _get_egg_link(dist.name)
                if egg_link:
                    self._install_editable_package(egg_link, dist)
                else:
                    spec = "{pkg_name}=={version}".format(pkg_name=pkg_name, version=dist.version)
                    self.run(
                        "{python} {installer} {installer_command} {spec}".format(
                            python=self.python, installer=installer, installer_command=installer_command, spec=spec
                        )
                    )
            else:
                self.run(
                    "{python} {installer} {installer_command} {spec}".format(
                        python=self.python, installer=installer, installer_command=installer_command, spec=pkg_name
                    )
                )
        else:
            spec = "{pkg_name}=={version}".format(pkg_name=pkg_name, version=version)
            self.run(
                "{python} {installer} {installer_command} {spec}".format(
                    python=self.python, installer=installer, installer_command=installer_command, spec=spec
                )
            )

    def installed_packages(self, package_type=None):
        """
        Return a package dict with
            key = package name, value = version (or '')
        """
        # Lazily install importlib_metadata in the underlying virtual environment
        self._install_importlib_metadata()
        if package_type is None:
            package_type = PackageEntry.ANY
        elif package_type not in PackageEntry.PACKAGE_TYPES:
            raise ValueError('invalid package_type parameter (%s)' % str(package_type))

        res = {}
        code = "import importlib_metadata as metadata\n"\
               "for i in metadata.distributions(): print(i.name + ' ' + i.version + ' ' + str(i.locate_file('')))"
        lines = self.run([self.python, "-c", code], capture=True).split('\n')
        for line in [i.strip() for i in lines if i.strip()]:
            name, version, location = line.split()
            res[name] = PackageEntry(name, version, location)
        return res

    def _install_importlib_metadata(self):
        if not self._importlib_metadata_installed:
            self.install_package("importlib_metadata", version=PackageVersion.CURRENT)
            self._importlib_metadata_installed = True

    def _install_editable_package(self, egg_link, package):
        python_dir = "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
        shutil.copy(egg_link, self.virtualenv / "lib" / python_dir / "site-packages" / egg_link.name)
        easy_install_pth_path = self.virtualenv / "lib" / python_dir / "site-packages" / "easy-install.pth"
        with open(easy_install_pth_path, "a") as pth, open(egg_link) as egg_link:
            pth.write(egg_link.read())
            pth.write("\n")
        for spec in package.requires:
            if not _is_extra_requirement(spec):
                dependency = next(pkg_resources.parse_requirements(spec), None)
                if dependency and (not dependency.marker or dependency.marker.evaluate()):
                    self.install_package(dependency.name, version=PackageVersion.CURRENT)


def _normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _get_egg_link(pkg_name):
    for path in sys.path:
        egg_link = pathlib.Path(path) / (pkg_name + ".egg-link")
        if egg_link.is_file():
            return egg_link
    return None


def _is_extra_requirement(spec):
    return any(x.replace(" ", "").startswith("extra==") for x in spec.split(";"))
