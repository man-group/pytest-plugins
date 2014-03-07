""" PkgLib organisation configuration
"""
import sys
import io
import ConfigParser
import os.path
import distutils
import itertools
from zipfile import ZipFile
from contextlib import closing

import pkg_resources

import errors


class Config(object):
    def __init__(self, **kwargs):
        [setattr(self, k, v) for (k, v) in kwargs.items()]

    def update(self, cfg):
        for k in cfg:
            if k not in self.__slots__:
                raise errors.UserError("Unknown config option: {0}".format(k))
            setattr(self, k, cfg[k])


ORG_SLOTS = ('pypi_url',
             'pypi_variant',
             'namespaces',
             'namespace_separator',
             'email_suffix',
             'dev_build_number',
             'platform_packages',
             'installer_search_path',
             'installer_dev_search_path',
             'default_platform_package',
             'deploy_path',
             'deploy_bin',
             'virtualenv_executable',
             'third_party_build_prefix',
             'sphinx_theme',
             'sphinx_theme_package',
             'graph_easy',
             'test_dirname',
             'test_egg_namespace',
             'test_linter',
             'test_linter_package',
             'jenkins_url',
             'jenkins_job_xml',
             'jenkins_matrix_job_xml',
             'jenkins_matrix_job_pyversions',
             )


class OrganisationConfig(Config):
    """ This object represents an organisation's packaging configuration.
    """
    __slots__ = ORG_SLOTS


ORG_MULTI_LINE_KEYS = ['namespaces', 'platform_packages', 'installer_search_path',
                       'installer_dev_search_path', 'virtualenv_executable',
                       'jenkins_matrix_job_pyversions']
PKG_MULTI_LINE_KEYS = ['install_requires', 'extras_require', 'setup_requires',
                       'tests_require', 'console_scripts', 'classifiers',
                       'scripts', 'description']

REQUIRES_KEYS = ['install_requires', 'setup_requires', 'tests_require']


# --------------------------------- INI-File parsing ---------------------------------- #

def parse_multi_line_value(v):
    """ Parses multi-line .ini file values into lists, with env interpolation. Eg::

        export ENV_VAR=abc

        foo =
            val1
            val2-${ENV_VAR}    ->  [val1, val2abc]
    """
    return [os.path.expandvars(i.strip())
            for i in v.split('\n')
            if i.strip()
            and not i.strip().startswith('#')
            ]


def parse_section(parser, section_name, multi_line_keys):
    """ Parses a ConfigParser section into a dict.

    Parameters
    ----------
    parser : `ConfigParser.ConfigParser`
        ConfigParser instance
    section_name : `str`
        Section name
    multi_line_keys : `list` of `str`
        List of multi-line keys
    """
    res = dict(parser.items(section_name))
    for k in multi_line_keys:
        res[k] = parse_multi_line_value(res.get(k, ''))
    return res


# ------------------------------ Organisation INI Parsing ---------------------------- #

def parse_org_metadata(parser):
    """
    Parse the organisation config from the given parser.
    """
    metadata = parse_section(parser, 'pkglib', ORG_MULTI_LINE_KEYS)
    # Handle disambiguation of underscores and dashes by making either work
    metadata['namespaces'] += [i.replace('_', '-')
                               for i in metadata['namespaces'] if '_' in i]
    return metadata


def setup_global_org_config(from_string=None, from_file=None, from_env="PKGLIB_CONFIG"):
    """
    Sets up the PkgLib global configuration.

    Parameters
    ----------
    from_string : `str`
        Reads from a string.
    from_file : `str`
        Reads from a file
    from_env : `str`
        Reads from a file nominated by ``from_env``.

    """
    p = ConfigParser.ConfigParser()
    if from_string:
        p.readfp(io.BytesIO(from_string))
    elif from_file:
        p.read(from_file)
    else:
        if not from_env in os.environ:
            distutils.log.debug("Can't configure PkgLib, missing environment "
                                "variable {0}".format(from_env))
            return
        if not os.path.isfile(os.environ[from_env]):
            raise errors.UserError("Can't configure PkgLib, unable to read "
                                   "config at {0}"
                                   .format(os.environ[from_env]))
        p.read(os.environ[from_env])

    import pkglib
    pkglib.CONFIG.update(parse_org_metadata(p))


# ----------------------------- Setup.cfg Parsing ------------------------------------ #

def get_pkg_cfg_parser(from_string=None):
    """
    Returns a ConfigParser for the ``setup.cfg`` file.

    Parameters
    ----------
    from_string : `str`
        Reads from a string. Otherwise assumes you're in the same
        dir as the ``setup.cfg`` file.

    Returns
    -------
    parser : `ConfigParser.ConfigParser`
        Parser instance
    """
    p = ConfigParser.ConfigParser()
    if from_string:
        p.readfp(io.BytesIO(from_string))
    else:
        p.read('setup.cfg')
    return p


def parse_extras_dependencies(dependencies_str):
    dependencies = []

    s = 0
    c = 0
    for i, ch in enumerate(dependencies_str + ","):
        if ch == "[":
            c = c + 1
        elif ch == "]":
            c = c - 1
        elif ch == "," and c == 0:
            d = dependencies_str[s:i].strip()
            s = i + 1
            if d:
                dependencies.append(d)

    return dependencies


def parse_extras_require_line(line):
    args = line.split(':')
    if len(args) != 2:
        raise RuntimeError("Invalid `extras_require` spec format: %s" % line)

    name = args[0].strip()
    if len(name) == 0:
        raise RuntimeError("Invalid `extras_require` (no name) : %s" % line)

    dependencies = args[1].strip()
    if len(dependencies) == 0:
        raise RuntimeError("Invalid `extras_require` (no extras) : %s" % line)

    return name, parse_extras_dependencies(dependencies)


def parse_extras_require(extras_require_list):
    res = {}
    for line in extras_require_list:
        n, d = parse_extras_require_line(line)
        res[n] = d
    return res


def clean_requires(reqs):
    """Removes requirements that aren't needed in newer python versions."""
    import pyenv
    return [req for req in reqs if not
            pyenv.included_in_batteries(pkg_resources.Requirement.parse(req), sys.version_info)]


def validate_metadata(metadata):
    if metadata['name'] != pkg_resources.safe_name(metadata['name']):
        raise RuntimeError("Package name '%s' contains illegal character(s); "
                           "consider changing to '%s'" %
                           (metadata['name'], pkg_resources.safe_name(metadata['name'])))

    return
    for section, reqs in ([(k, metadata[k]) for k in REQUIRES_KEYS] +
                          [('extras_require[%s]' % k, v) for k, v in
                           metadata['extras_require'].items()]):
        for s in reqs:
            req = pkg_resources.Requirement.parse(s)
            if req.unsafe_name != req.project_name:
                raise RuntimeError("Invalid name '%s' in requirement '%s' for "
                                   "'%s' of '%s'; consider changing to '%s'"
                                   % (req.unsafe_name, s, section,
                                      metadata['name'], req.project_name))


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
            distutils.log().warn("Can't find importlib to read package description.")
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


def parse_pkg_metadata(parser, validate=True):
    """
    Parse the metadata section in the ``setup.cfg`` file.

    Parameters
    ----------
    parser : `ConfigParser.ConfigParser`
        ConfigParser instance for the ``setup.cfg`` file
    """
    import util
    metadata = parse_section(parser, 'metadata', PKG_MULTI_LINE_KEYS)

    metadata['description'] = " ".join(metadata.get('description', []))

    metadata['extras_require'] = parse_extras_require(metadata.get('extras_require', []))

    # Update the long description based off of README,CHANGES etc.
    metadata['long_description'] = get_pkg_description(metadata)

    # Determine namespace packages based off of the name
    metadata['namespace_packages'] = util.get_namespace_packages(metadata['name'])

    # Overrides from setup.cfg file. console_scripts is a bit special in this
    # regards as it lives under entry_points
    entry_points = metadata.setdefault('entry_points', {})
    if parser.has_section('entry_points'):
        for k, v in parser.items('entry_points'):
            entry_points.setdefault(k, []).extend(parse_multi_line_value(v))
    if 'console_scripts' in metadata:
        entry_points.setdefault('console_scripts', []
                                ).extend(metadata.pop('console_scripts'))

    for reqs in itertools.chain([metadata[k] for k in REQUIRES_KEYS],
                                metadata['extras_require'].values()):
        reqs[:] = clean_requires(reqs)

    if validate:
        validate_metadata(metadata)

    return metadata


# --------------------------- allrevisions.txt Parsing ------------------------------- #

def read_allrevisions_file(f):
    """
    Parse an 'allrevisions.txt' file.

    Parameters
    ----------
    f : `Iterable` of `str`
        Lines of the 'allrevisions.txt' file - can be an open file.

    Returns
    -------
    res : `list` of `tuple`
        pkg_name, pkg_version, url, revision
    """
    res = []
    for line in f:
        if line.startswith('#'):
            continue
        row = line.strip().split(',')
        if len(row) < 4:
            continue
        res.append((row[0], row[1], row[2], int(row[3])))
    return res


def read_allrevisions(egg, project_name=None):
    """
    Read the allrevisions.txt file from out of an egg file or directory
    """
    if os.path.isfile(egg):
        with closing(ZipFile(egg)) as z:
            return read_allrevisions_file(z.open('EGG-INFO/allrevisions.txt'))
    if os.path.isdir(os.path.join(egg, 'EGG-INFO')):
        with open(os.path.join(egg, 'EGG-INFO', 'allrevisions.txt')) as f:
            return read_allrevisions_file(f)
    if project_name is not None:
        egg_info = os.path.join(egg, '%s.egg-info' % pkg_resources.to_filename(project_name))
        if os.path.isdir(egg_info):
            with open(os.path.join(egg_info, 'allrevisions.txt')) as f:
                return read_allrevisions_file(f)
    raise IOError('Not an egg', egg)
