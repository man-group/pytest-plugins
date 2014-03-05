"""
PkgLib Testing Library
===================

This library contains useful helpers for writing unit and acceptance tests.
"""

from pkglib_testing import config

# Global config for finding system resources.
# Set this up using pkglib_testing.setup_testing_config

CONFIG = config.TestingConfig(
    java_executable="java",
    jenkins_url=None,
    jenkins_war=None,
    mongo_bin="/usr/sbin",
    redis_executable="/usr/sbin/redis-server",
)