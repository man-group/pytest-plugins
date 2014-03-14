'''
Created on 10 Mar 2014

@author: edeaston
'''
# We should always start with an empty testing package config
import os
import pkglib
from pkglib.config import org

os.unsetenv('PKGLIB_CONFIG')

pkglib.CONFIG = org.OrganisationConfig(
    pypi_url='http://acmepypi.example.com',
    pypi_variant=None,
    pypi_default_username=None,
    pypi_default_password=None,
    namespaces=['acme'],
    namespace_separator='.',
    third_party_build_prefix='acme',
    email_suffix='acme.example',
    dev_build_number='0.0',
    platform_packages=[],
    installer_search_path=[],
    installer_dev_search_path=[],
    default_platform_package=None,
    deploy_path='/deploy/to/nowhere',
    deploy_bin='/run/from/nowhere',
    vcs='svn',
    virtualenv_executable='virtualenv',
    sphinx_theme='pkglib.sphinx.default_theme',
    sphinx_theme_package=None,
    graph_easy=None,
    test_egg_namespace="acmetests",
    test_linter="flake8",
    test_linter_package="flake8",
    test_dirname="tests",
    jenkins_url=None,
    jenkins_job_xml=None,
    jenkins_matrix_job_xml=None,
    jenkins_matrix_job_pyversions=None,
)
