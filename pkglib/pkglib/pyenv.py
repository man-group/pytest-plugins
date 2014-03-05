# from __future__ import absolute_import

import os
import logging
import re
import sys
import tempfile
import inspect
from distutils.version import LooseVersion
from pickle import loads
from contextlib import contextmanager

import pkg_resources

import cmdline
import util
from .setuptools.command import base


# List of packages in the working set that are treated as 'system' packages and
# excluded from general package listings.
#  - Includes pkglib as it is packaging code hidden from general use
#  - Includes pip, setuptools and distribute for the same reasons. Unfortunately
#    these may be specified by 3rd party packages, so they would still be found
#    even if we followed dependencies rather than looking at every package in the
#    working set.
#  - Even though wsgiref is a built-in package, Python 2.7 ships an egg-info file
#    for it: http://bugs.python.org/issue12218
SYSTEM_PACKAGES = ('pkglib', 'distribute', 'pip', 'python', 'setuptools', 'wsgiref')


def get_log():
    return logging.getLogger(__name__)


def included_in_batteries(req, version=sys.version_info):
    """ Returns True if the given requirement is included in the
        standard library at a given version
    """
    NEW_IN = {'importlib': (2, 7),
              'contextlib2': (3, 3),
              }
    return req.key in NEW_IN and version >= NEW_IN[req.key]


def get_site_packages(root=sys.exec_prefix, version=sys.version_info):
    """ Returns the site-packages dir for this virtualenv
    """
    return os.path.join(os.path.abspath(root), 'lib',
                        util.short_version(version, prefix='python', max_parts=2),
                        'site-packages')


def py_version(version):
    return util.short_version(version, 2, prefix="py")


def resolve_virtualenv_cmd(virtualenv_cmd=None):
    """ Look for virtualenv.
    """
    if virtualenv_cmd is not None:
        return virtualenv_cmd

    for prospect in CONFIG.virtualenv_executable:
        if cmdline.which(prospect):
            return prospect
    raise RuntimeError("Unable to resolve virtualenv installation to use, "
                       "tried %s" % CONFIG.virtualenv_executable)


def clean_env_of_python_vars(remove_ld_library_path=False):
    """  Returns a copy of the current environment with all the variables
         associated with Python, such as 'PYTHONPATH' or 'PYTHONHOME'
         removed.
    """
    env = dict(os.environ)

    var_prefixes = ["VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"]
    if remove_ld_library_path:
        var_prefixes.append("LD_LIBRARY_PATH")

    for prefix in var_prefixes:
        for v in list(env.keys())[:]:
            if v.strip().upper().startswith(prefix):
                del env[v]
    return env


def _prepend_env_path_var(env, name, value):
    path = value
    if name in env:
        path = os.path.pathsep.join((path, env[name]))
    env[name] = path


def _python_info_dump():
    """ Function that is run in an subprocess to introspect system information
    """
    import sys  # @Reimport
    from distutils import util, sysconfig  # @Reimport
    print(".".join(str(v) for v in sys.version_info))
    print(sys.prefix)
    print(getattr(sys, "real_prefix", sys.prefix))
    print(1 if hasattr(sys, "gettotalrefcount") else 0)
    print(sys.hexversion)
    print(".".join(str(s) for s in getattr(sys, "subversion", "") if s))
    print(util.get_platform())
    print(sysconfig.get_config_var("LIBDIR") or "")


def _python_get_deps(package_name):
    """ Function that is run in a subprocess to return active dependencies
        of a given package.
    """
    from pkglib.setuptools.dependency import get_all_requirements, get_dist
    pkg = get_dist(package_name).project_name
    if pkg:
        try:
            print('\n'.join(d.project_name for d in
                            get_all_requirements([pkg], True)))
        except:
            print('\n'.join(d.project_name for d in
                            get_all_requirements([pkg])))


def _get_installed_packages(skip=SYSTEM_PACKAGES):
    """ Function that is run in a subprocess to return all active packages, excluding the
        'system' packages.
    """
    from pkg_resources import working_set
    from pickle import dumps
    print(dumps([(d.project_name, d.version) for d in working_set if d.key not in skip]))


class PythonInstallation(object):
    """ Class that represents a Python installation (or virtual environment)
        with helper methods to get dependencies, paths and perform actions.
    """
    log = logging.getLogger("PythonInstallation")

    def __init__(self, executable):
        self.log.info("Reading Python installation details from: %s" % executable)
        cmd = [executable, "-c", inspect.getsource(_python_info_dump) +
               '\n_python_info_dump()']
        info = cmdline.run(cmd, env=clean_env_of_python_vars(remove_ld_library_path=True)).split("\n")

        self.version = LooseVersion(info[0] + (".debug" if info[3] == "1" else ""))
        self.prefix = os.path.realpath(info[1])
        self.real_prefix = os.path.realpath(info[2])
        self.hexversion = info[4]
        self.subversion = info[5]
        self.platform = info[6]
        self.libdir = info[7]
        self.executable = executable
        self.bindir = os.path.dirname(self.executable)
        real_prefix_executable = os.path.join(self.real_prefix, "bin", "python")
        self.real_executable = (real_prefix_executable
                                if (os.path.isfile(real_prefix_executable) and
                                    os.access(real_prefix_executable, os.X_OK))
                                else executable)

    def __str__(self, *args, **kwargs):  # @UnusedVariable
        return self.__repr__()

    def __repr__(self, *args, **kwargs):  # @UnusedVariable
        return "<Python [%s] at: %s>" % (self.version.vstring, self.prefix)

    def _make_env(self):
        env = clean_env_of_python_vars()
        _prepend_env_path_var(env, "PATH", os.path.dirname(self.executable))
        _prepend_env_path_var(env, "LD_LIBRARY_PATH", self.libdir)
        return env

    @contextmanager
    def _local_temp(self):
        tmp = reduce(lambda x, y: x if x else os.environ.get(y),
                     ["TMPDIR", "TEMP", "TMP"], None)
        if not tmp:
            old_tempdir = tempfile.tempdir
            tempfile.tempdir = tmp
            try:
                tmp = os.path.join(self.prefix, ".temp")
                with cmdline.set_env(TMPDIR=tmp):
                    yield tmp
            finally:
                tempfile.tempdir = old_tempdir
        else:
            yield tmp

    def short_version(self, max_parts=None, prefix=None, suffix=None,
                      separator=DEFAULT_VERSION_SEP):
        return util.short_version(self.version, max_parts=max_parts,
                             prefix=prefix, suffix=suffix, separator=separator)

    def py_version(self):
        return py_version(self.version)

    def run(self, cmd, **kwargs):
        return cmdline.run(cmd, env=self._make_env(), **kwargs)

    def run_cmd_from_bin(self, *cmd, **kwargs):
        cmd = util.flatten(cmd)
        return self.run([os.path.join(self.bindir, cmd[0])] + util.flatten(cmd[1:]),
                        **kwargs)

    def run_python_cmd(self, *cmd, **kwargs):
        return self.run([self.executable] + util.flatten(cmd), **kwargs)

    def get_package_dependencies(self, package_name):
        cmd = (inspect.getsource(_python_get_deps) +
               '\n_python_get_deps({0!r})'.format(package_name))
        out = self.run_python_cmd('-c', cmd, capture_stdout=True)
        return [d for d in out.split('\n') if d]

    def get_installed_packages(self):
        """
        Return packages installed in a given virtualenv.

        Returns
        -------
        package_info : `list`
            list of tuples (name, version)
        """
        cmd = inspect.getsource(_get_installed_packages) + '\n_get_installed_packages()'
        return loads(self.run([self.executable, '-c', cmd], capture_stdout=True, cwd=self.libdir))

    def setup_package(self, pkg_dir, test=True, deps=True, build=True,
                      pypi_index_url=None, prefer_final=False,
                      debug=False, verbose=False):
        """
        Setup a package in this python installation using
        `python setup.py develop`.

        Parameters
        ----------
        pkg_dir : `str`
            package checkout dir
        options : `optparse.Options`
            command-line options
        test : `bool`
            True/False will install test packages
        """

        self.log.info("Setting up package in: %s" % pkg_dir)
        cmd = ['setup.py']
        if debug:
            cmd.append('-v')
        cmd.append('develop')
        if pypi_index_url:
            cmd.extend(['-i', util.maybe_add_simple_index(pypi_index_url)])
        if not test:
            cmd.append('--no-test')
        if not deps:
            cmd.append('--no-deps')
        if not build:
            cmd.append('--no-build')
        if prefer_final:
            cmd.append('--prefer-final')

        return self.run_python_cmd(cmd, capture_stdout=not verbose, capture_stderr=not verbose,
                                   cwd=pkg_dir)

    def install_package(self, pkg_name, deps=True, installer="easy_install",
                        pypi_index_url=None, debug=False, verbose=False,
                        dev=True):
        """
        Install a package in the given virtualenv.
        """
        get_log().info('Installing package [%s]' % pkg_name)
        # would like to install with --no-deps, but we want to know about 3rd
        # party package versions.
        cmd = [os.path.join(self.bindir, installer)]
        if dev and installer == 'pyinstall':
            # use 'dev' mode for pyinstall to pick up latest dev versions if
            # they're available (easy_install uses dev versions anyway)
            cmd.append('--dev')
        if debug:
            cmd.append('-v')
        if pypi_index_url:
            cmd.extend(['-i', base.maybe_add_simple_index(pypi_index_url)])
        if not deps:
            cmd.append('--no-deps')

        cmd.append(pkg_name)
        self.run_python_cmd(cmd, capture_stdout=not verbose)

    def install_pkgutils(self, **kwargs):
        """
        Install ahl.pkgutils into the given virtualenv. Same argument

        Parameters
        ----------
        Same as install_package()
        """
        self.install_package("ahl.pkgutils", **kwargs)

    def get_package_location(self, pkg_name):
        key = pkg_resources.safe_name(pkg_name).lower()
        cmd = r"""
from pkg_resources import working_set
print(working_set.by_key[%r].location)""" % key
        return self.run_python_cmd(['-c', cmd], capture_stdout=True, cwd='/'
                                   ).strip()

    def show_dependency_graph(self, pkg_dir=None, pkg_name=None, verbose=False):
        """
        Show dependency graph using invoking `pydepgraph`

        Parameters
        ----------
        virtualenv : `str`
            virtulenv base dir
        pkg_dir : `str`
            package checkout dir
        pkg_name : `str`
            package name
        options : `optparse.Options`
            command-line options
        """
        if pkg_dir:
            get_log().info("Showing dependency graph for checkout at: %s" % pkg_dir)
            self.run_python_cmd(['setup.py', 'depgraph'], capture_stdout=not verbose, cwd=pkg_dir)
        else:
            get_log().info("Showing dependency graph for package [%s]" % pkg_name)
            self.run_cmd_from_bin("pydepgraph", pkg_name, capture_stdout=not verbose)

    def bin_contains_file(self, filename):
        return os.path.isfile(os.path.join(self.bindir, filename))


def resolve_python(python=None):
    """ Resolve a string path or `PythonInstallation` to its real location.
        With no input, uses the current interpreter.
    """
    if isinstance(python, PythonInstallation):
        python = python.real_executable
    else:
        if not python:
            python = sys.executable
        python = PythonInstallation(python).real_executable
    return python


def create_virtualenv(dest, virtualenv_cmd=None, virtualenv_args='',
                      python=None, verbose=False):
    """
    Creates new Python virtual environment.

    Parameters
    ----------
    dest : `str`
        Destination directory path
    virtualenv_cmd : `str`
        a path to virtualenv script which will be used to create the virtual
        environment. If not provided an attempt will be made to get the path
        for virtualenv script from CONFIG.virtualenv_executable, or failing
        that the following environment variables:

            * "VIRTUALENV_CMD"
            * "VIRTUALENVWRAPPER_VIRTUALENV"

        A RuntimeError is raised if virtualenv command cannot be resolved.
    virtualenv_args : `str`
        arguments to pass to virtualenv script
    python : `str`
        a path to Python executable which virtualenv will be using (defaults to
        current Python executable). If path is not found a RuntimeError is
        raised.
    verbose : `bool`
        whether to show command output (defaults to False)
    """

    virtualenv_cmd = resolve_virtualenv_cmd(virtualenv_cmd)
    python = resolve_python(python)

    base = os.path.dirname(dest)
    if not os.path.isdir(base):
        os.makedirs(base)

    get_log().info("Creating new Python virtual environment at: %s" % dest)
    out = cmdline.run([virtualenv_cmd, virtualenv_args, "-p", python, dest], capture_stdout=True,
                      env=clean_env_of_python_vars(remove_ld_library_path=True))
    if verbose:
        print(out)
    out = re.match("New +python +executable +in +([^\n ]*)", out)
    executable = out.group(1) if out else os.path.join(dest, "bin", "python")
    if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
        raise RuntimeError("Unable to verify the location of created "
                           "Python executable at: %s" % dest)

    return os.path.realpath(executable)
