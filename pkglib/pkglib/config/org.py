""" PkgLib organisation configuration
"""
import os
import io
import distutils

import ConfigParser as configparser

from . import Config
from .. import errors

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


# ------------------------------ Organisation INI Parsing ---------------------------- #

def parse_org_metadata(parser):
    """
    Parse the organisation config from the given parser.
    """
    import parse
    metadata = parse.parse_section(parser, 'pkglib', ORG_MULTI_LINE_KEYS)
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
    p = configparser.ConfigParser()
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

    from .. import CONFIG
    CONFIG.update(parse_org_metadata(p))
