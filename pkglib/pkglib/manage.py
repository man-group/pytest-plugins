"""
Module for working with Python packages.

"""
import logging
import os

from pkg_resources import parse_requirements, working_set

from pkglib import CONFIG, config
import cmdline


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
            for req in parse_requirements(
                list(r for r in metadata.get('install_requires', [])
                     if is_inhouse_package(r))):
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
        dists = [d for d in working_set if d.project_name == pkg]
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
