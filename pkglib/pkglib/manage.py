"""
Module for working with Python packages.

"""
import logging
import sys
import os
import re
import itertools

from pkg_resources import parse_requirements, working_set
from contextlib import contextmanager

from pkglib import CONFIG, config

from cmdline import run


def get_log():
    return logging.getLogger("pkglib.manage")

RE_DEV_VERSION = re.compile('\.dev\d*$')


# Common options arg must support:
#  pyenv: name of virtualenv  to work with
#  verbose: verbose logging
#  pypi: pypi instance
#  prefer_final: use only final packages


class DEFAULT_OPTIONS(object):
    # XXX clean up default options for all these methods
    verbose = True
    no_action = False


# TODO get rid of this and use pkg_resources.parse_version for (more correct) version comparison.
class PackageVersion(object):
    """This class wrapps a package version so that they can be
    compared.

    """

    def __init__(self, version):
        self.version = version

    def isdev(self):
        return is_dev_version(self.version)

    def __str__(self):
        return self.version

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.version)

    def __cmp__(self, rhs):
        def normalize(a, b):
            try:
                ai = int(a)
                bi = int(b)
                return ai, bi
            except ValueError:
                return a, b

        al = self.version.split(".")
        bl = rhs.version.split(".")

        for a, b in itertools.izip(al, bl):
            a, b = normalize(a, b)
            rc = cmp(a, b)
            if rc:
                return rc
        return len(al) - len(al)


@contextmanager
def chdir(dirname):
    """
    Context Manager to change to a dir then change back
    """
    here = os.getcwd()
    os.chdir(dirname)
    yield
    os.chdir(here)


@contextmanager
def set_home(dirname):
    """
    Context Mgr to set HOME
    """
    old_home = os.environ['HOME']
    os.environ['HOME'] = dirname
    yield
    os.environ['HOME'] = old_home


def is_inhouse_package(name):
    """
    True if this package is an in-house package
    """
    for prefix in CONFIG.namespaces:
        if name.startswith(prefix + CONFIG.namespace_separator):
            return True
    return False


def is_dev_version(version):
    """
    True if this version is a dev version
    """
    return RE_DEV_VERSION.search(version)


def is_strict_dev_version(version):
    """
    True if this version is a dev version, and the numeric component matches
    our static build number.
    """
    # This one matches only versions that also match our dev build version
    strict_re = re.compile('^{}\.dev\d*$'
                           .format(CONFIG.dev_build_number.replace('.', '\.')))
    return strict_re.search(version)


def get_build_egg_dir():
    """
    Returns the path to the directory where tests_require dependenies
    are installed into
    """
    return os.path.join(os.getcwd(), '.build-eggs')


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
    run(cmd, capture_stdout=not options.verbose)


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
    from path import path as p
    get_log().info("%s Setting up package in %s" % (indent_txt, pkg_dir))
    if getattr(options, 'no_action', False):
        return
    python = p(virtualenv) / 'bin' / 'python'
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
    with chdir(pkg_dir):
        run(cmd, capture_stdout=not options.verbose)


def get_inhouse_dependencies(pkg_dir, exceptions=[], indent_txt=''):
    """
    Yields a list of dependencies to setup.
    """
    with chdir(pkg_dir):
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
    run([virtualenv_cmd, dest, '--distribute'], env=env)


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
    run([os.path.join(virtualenv, 'bin', 'python'),
         os.path.join(virtualenv, 'bin', 'easy_install'), requirement])


def get_pkg_description(metadata):
    """
    Returns the long description text for the given package metadata, based
    off its ``README.txt`` or package ``__init__.py`` file and changelog.
    Assumes we're running this within a package root.

    Parameters
    ----------
    metadata : `dict`
        Package metadata dictionary as returned from `parse_metadata`
    """
    # XXX Not yet working, something wrong with the imports :(
    return ''

    readme = ''
    try:
        readme = open('README.txt').read()
    except IOError:
        # Need to handle this gracefully, this function gets called when
        # bootstrapping pkglib, importlib might not exist at this point.
        try:
            import importlib
        except ImportError:
            get_log().warn("Can't find importilb to read package description.")
        else:
            mod = importlib.import_module(metadata['name'])
            readme = mod.__doc__
            # Some ambiguity here whether or not the module is yet importable.
            # Do a relative import based on the package name
            # parts = metadata['name'].rsplit('.', 1)
            # if len(parts) == 1:
            #    readme = importlib.import_module(parts[0]).__doc__
            # else:
                # ns, modname = parts
                # ns_dir = ns.replace('.', os.sep)
                # with chdir(ns_dir):
                #    sys.path.insert(0, ns_dir)
                #    import pdb; pdb.set_trace()
                #    readme = importlib.import_module(modname).__doc__
    try:
        changes = open('CHANGES.txt').read()
    except IOError:
        changes = ''
    return readme + '\n\n' + changes


def read_allrevisions_file(fname):
    """Read lines from this csv-like file and return list of row data."""
    res = []
    with open(fname) as fp:
        for line in fp:
            if line.startswith('#'):
                continue
            row = line.strip().split(',')
            if len(row) < 4:
                continue
            # return pkg_name, pkg_version, url, revision
            res.append((row[0], row[1], row[2], int(row[3])))
    return res


def get_namespace_packages(name):
    """
    Returns all the namespace packages for a given package name
    >>> get_namespace_packages('foo')
    []
    >>> get_namespace_packages('foo.bar')
    ['foo']
    >>> get_namespace_packages('foo.bar.baz')
    ['foo', 'foo.bar']
    """
    parts = name.split(CONFIG.namespace_separator)
    if len(parts) < 2:
        return []
    res = []
    for i in range(len(parts) - 1):
        res.append('.'.join(parts[:i + 1]))
    return res


def get_site_packages():
    """ Returns the site-packages dir for this virtualenv
    """
    from path import path
    return (path(sys.exec_prefix).abspath() / 'lib' /
            ('python{0}.{1}'.format(*sys.version_info[:2])) / 'site-packages')
