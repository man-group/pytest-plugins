""" PkgLib organisation configuration
"""
import io
import ConfigParser
import os.path

import errors


class Config(object):
    def __init__(self, **kwargs):
        [setattr(self, k, v) for (k, v) in kwargs.items()]


class OrganisationConfig(Config):
    __slots__ = ['pypi_url',
                 'namespaces',
                 'email_suffix',
                 'dev_build_number',
                 'platform_packages',
                 'installer_search_path',
                 'default_platform_package',
                 'deploy_path',
                 'deploy_bin',
                 'vcs',
                 'virtualenv_executable',
                 'sphinx_theme',
                 'sphinx_theme_package',
                 'graph_easy',
                 'test_egg_namespace',
                 'test_linter',
                 'test_linter_package',
                 'jenkins_url',
                ]


class TestinConfig(Config):
    __slots__ = ['java_executable',
                 'jenkins_war',
                 'mongo_bin',
                 'redis_executable',
                 ]


ORG_MULTI_LINE_KEYS = ['namespaces', 'platform_packages']
PKG_MULTI_LINE_KEYS = ['install_requires', 'setup_requires', 'tests_require', 'console_scripts',
                       'classifiers', 'scripts', 'description']


def _parse_metadata(parser, section, multi_line_keys):
    metadata = dict(parser.items(section))
    for k in multi_line_keys:
        metadata[k] = [os.path.expandvars(i.strip()) for i in metadata.get(k, '').split('\n') if i.strip()
                       and not i.strip().startswith('#')]
    return metadata


def setup_org_config(from_string=None, from_file=None, from_env="PKGLIB_CONFIG"):
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
            raise errors.UserError("Can't setup PkgLib, missing environment variable {0}".format(from_env))
        if not os.path.isfile(os.environ[from_env]):
            raise errors.UserError("Can't setup PkgLib, can't read config at {0}"
                                   .format(os.environ[from_env]))
        p.read(os.environ[from_env])

    import pkglib
    set_config(pkglib.CONFIG, parse_org_metadata(p))


def parse_org_metadata(parser):
    """
    Parse the organisation config from the given parser.
    """
    metadata = _parse_metadata(parser, 'pkglib', ORG_MULTI_LINE_KEYS)
    # This is to handle setuptools' ridiculous policy of converting underscores to dashes
    metadata['namespaces'] += [i.replace('_', '-') for i in metadata['namespaces'] if '_' in i]
    return metadata


def set_config(config_obj, metadata_dict):
    """
    Set attributes from a metadata dict on the given config object
    """
    for k in metadata_dict:
        if k not in config_obj.__slots__:
            raise errors.UserError("Unknown config option: {0}".format(k))
        setattr(config_obj, k, metadata_dict[k])


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


def parse_pkg_metadata(parser):
    """
    Parse the package metadata section in the ``setup.cfg`` file.

    Parameters
    ----------
    parser : `ConfigParser.ConfigParser`
        ConfigParser instance for the ``setup.cfg`` file
    """
    return _parse_metadata(parser, 'metadata', PKG_MULTI_LINE_KEYS)
