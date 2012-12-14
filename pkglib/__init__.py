""" PkgLib - a company-centric packaging and testing library
"""
import config

# Organisation configuration, this is updated when calling pkglib.setuptools.setup(my_config)
CONFIG = config.OrganisationConfig(pypi_url='http://pypi.python.org',
                                   namespaces=['acme'],
                                   email_suffix='acme.example',
                                   dev_build_number='0.0',
                                   platform_packages=[],
                                   default_platform_package=None,
                                   deploy_path='${HOME}/pydeploy/packages',
                                   deploy_bin='${HOME}/pydeploy/bin',
                                   vcs='svn',
                                   virtualenv_executable='virtualenv',
                                   sphinx_theme='pkglib.sphinx.default_theme',
                                   sphinx_theme_package=None,
                                   graph_easy=None,
                                   test_egg_namespace="acmetests",
                                   test_linter="flake8",
                                   test_linter_package="flake8",
                                   java_executable="java",
                                   jenkins_url=None,
                                   jenkins_war=None,
                                   mongo_bin="/usr/sbin",
                                   redis_executable="/usr/sbin/redis-server",
                                   )
