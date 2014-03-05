"""
Module for working with Python packages.

"""
import logging
import os
import sys

import pkg_resources

from pkglib import CONFIG
import config
import util
import cmdline
import pyenv
import errors


def get_log():
    return logging.getLogger(__name___)


# Common options arg must support:
#  pyenv: name of virtualenv  to work with
#  verbose: verbose logging
#  pypi: pypi instance
#  prefer_final: use only final packages


class DEFAULT_OPTIONS(object):
    # XXX clean up default options for all these methods
    verbose = True
    no_action = False


def checkout_pkg(dest_dir, pypi, pkg, options, branch='trunk', indent_txt='', vcs='svn'):
    """
    Checks out a package by name to a specified dest dir

    Parameters
    ----------
    dest_dir : `str`
        Destination dir
    pypi : `pkglib.pypi.PyPi`
        PyPi API
    pkg : `str`
        Package Name
    branch : `str`
        VCS branch name
    options : `optparse.Options`
        Cmdline options
    """
    if os.path.isfile(os.path.join(dest_dir, 'setup.py')):
        get_log().info("%s %s already checked out" % (indent_txt, pkg))
        return

    uri = pypi.get_vcs_uri(pkg)

    if vcs == 'svn':
        uri = '%s/%s' % (uri, branch)
        cmd = ['svn' 'co', uri, dest_dir]
    else:
        raise ValueError("Unsupported vcs: {0}".format(vcs))

    get_log().info("%s Checking out %s from %s" % (indent_txt, pkg, uri))
    if getattr(options, 'no_action', False):
        return
    cmdline.run(cmd, capture_stdout=not options.verbose)


def setup_pkg(virtualenv, pkg_dir, options, test=True, indent_txt='',
              deps=True):
    """
    Sets up a package in the given virtualenv

    Parameters
    ----------
    virtualenv : `str`
        virtulenv base dir
    pkg_dir : `str`
        package checkout dir
    options : `optparse.Options`
        command-line options
    test : `bool`
        True/False will install test packages
    deps : `bool`
        True/False will install dependencies
    """
    get_log().info("%s Setting up package in %s" % (indent_txt, pkg_dir))
    if getattr(options, 'no_action', False):
        return
    python = os.path.join(virtualenv, 'bin', 'python')
    cmd = [python, 'setup.py']
    if options.verbose:
        cmd.append('-v')
    cmd.append('develop')
    if not test:
        cmd.append('--no-test')
    if getattr(options, 'prefer_final', False):
        cmd.append('--prefer-final')
    if not deps:
        cmd.append('--no-deps')
    with cmdline.chdir(pkg_dir):
        cmdline.run(cmd, capture_stdout=not options.verbose)


def get_inhouse_dependencies(pkg_dir, exceptions=[], indent_txt=''):
    """
    Yields a list of dependencies to setup.
    """
    with cmdline.chdir(pkg_dir):
        if os.path.isfile('setup.cfg'):
            metadata = config.parse_pkg_metadata(config.get_pkg_cfg_parser())
            for req in pkg_resources.parse_requirements(
                list(r for r in metadata.get('install_requires', [])
                     if util.is_inhouse_package(r))):
                if req.project_name not in exceptions:
                    yield req.project_name
        else:
            get_log().warn("{0} Package at {1} has no setup.cfg file, cannot "
                           "find dependencies.".format(indent_txt, pkg_dir))


def create_virtualenv(dest, virtualenv_cmd=None):
    """
    Create Python Virtualenv for deployment.
    Unsets ``PYTHONPATH`` to ensure it is a clean build
    (I'm looking at you, Eclipse..)

    Parameters
    ----------
    dest : `str`
        Destination directory path

    """
    if virtualenv_cmd == None:
        virtualenv_cmd = CONFIG.virtualenv_executable
    print "Creating virtualenv at %s" % dest
    base = os.path.dirname(dest)
    if not os.path.isdir(base):
        os.makedirs(base)
    env = dict(os.environ)
    if 'PYTHONPATH' in env:
        del(env['PYTHONPATH'])
    cmdline.run([virtualenv_cmd, dest, '--distribute'], env=env)


def install_pkg(virtualenv, pkg, options=DEFAULT_OPTIONS, version=None,
                allow_source_package=False):
    """
    Install package in the given virtualenv

    Parameters
    ----------
    virtualenv : `str`
        Virtualenv base path
    pkg : `str`
        Package name
    version : `str`
        Package version, defaults to latest available
    allow_source_package : `bool`
        If the package is setup as a source package in the current runtime
        context, set it up from there otherwise use easy_install.
    """
    requirement = pkg
    if allow_source_package:
        dists = [d for d in pkg_resources.working_set if d.project_name == pkg]
        if dists and not dists[0].location.endswith('.egg'):
            setup_pkg(virtualenv, dists[0].location, options)
            return

    if version:
        requirement = '%s==%s' % (pkg, version)
    get_log().info("Installing requirement %s" % requirement)
    if getattr(options, 'no_action', False):
        return

    # Using easy_install as an argument here to get around #! path limits
    cmdline.run([os.path.join(virtualenv, 'bin', 'python'),
                 os.path.join(virtualenv, 'bin', 'easy_install'), requirement])


def deploy_pkg(egg_or_req, python=sys.executable, package_base=None,
               console_script_base=None, pypi_index_url=None):
    """ Deploys a package to a versioned, isolated virtual environment in a package
        base directory. Maintains a 'current' symlink to the last version that
        was deployed.

    Parameters
    ----------
    egg_or_req : `str`
        Either a string requirement (eg, 'foo==1.2') or the path to an egg file.
    python : `str` or `pyenv.PythonInstallation`
        Python interpreter from which the python interpreter is derived
    package_base: `str`
        Path to package base directory under which the versioned virtual environment
        is created.
    console_script_base: `str`
        Path to directory into which all the console scripts for the deployed package
        are symlinked.
    """
    package_base = package_base or CONFIG.deploy_path
    console_script_base = console_script_base or CONFIG.deploy_bin

    try:
        req = pkg_resources.Requirement.parse(egg_or_req)
    except ValueError:
        req = pkg_resources.Distribution.from_filename(egg_or_req).as_requirement()
    version = next(ver for op, ver in req.specs if op == '==')

    package_dir = os.path.join(package_base, req.project_name)
    if not isinstance(python, pyenv.PythonInstallation):
        python = pyenv.PythonInstallation(python)

    pyenv_dir = os.path.join(package_dir, version,
                             python.short_version(3, prefix="PYTHON_"))

    if os.path.isdir(pyenv_dir):
        raise errors.UserError("Package [%s] version [%s] is already installed at: %s"
                               % (req.project_name, version, pyenv_dir))

    # Set umask for file creation: 0022 which is 'rwx r.x r.x'
    with cmdline.umask(0o022):
        virtualenv = pyenv.VirtualEnv(force_dir=os.path.abspath(pyenv_dir),
                                      delete=False, python=python, verbose=False)
        virtualenv.install_pkgutils(verbose=False,
                                    pypi_index_url=pypi_index_url)
        virtualenv.install_package(egg_or_req, installer='pyinstall',
                                   debug=True, verbose=False,
                                   pypi_index_url=pypi_index_url, dev=False)

        current_link = os.path.join(package_dir, 'current')
        if os.path.islink(current_link):
            get_log().info("removing current link %s" % current_link)
            os.unlink(current_link)

        base = os.path.abspath(os.path.join(pyenv_dir, os.pardir, os.pardir))
        relative_link = pyenv_dir[len(base):].lstrip(os.path.sep)
        get_log().info("creating current link %s -> %s" % (current_link, relative_link))
        os.symlink(relative_link, current_link)

        if not os.path.isdir(console_script_base):
            get_log().info("creating console script base: %s" % console_script_base)
            os.makedirs(console_script_base)

        scripts = virtualenv.run_python_cmd(['-c', r"""
from pkg_resources import working_set
dist = working_set.by_key[{0!r}]
print('\n'.join(dist.get_entry_map().get('console_scripts', {{}}).keys()))
""".format(req.key)]).split()
        get_log().warn(scripts)
        for item in scripts:
            src = os.path.join(console_script_base, item)
            dest = os.path.join(current_link, 'bin', item)
            if os.path.islink(src):
                get_log().info("Removing console script link: %s" % src)
                os.unlink(src)

            get_log().info("linking console script %s -> %s" % (src, dest))
            os.symlink(dest, src)
