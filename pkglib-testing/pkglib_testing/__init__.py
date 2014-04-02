"""
PkgLib Testing Library
===================

This library contains useful helpers for writing unit and acceptance tests.
"""
import os
import socket

from pkglib_testing import config

# Global config for finding system resources.
# This can be set this up using pkglib_testing.setup_testing_config

CONFIG = config.TestingConfig(
    # Not using localhost here in case we are being used in a cluster-type job
    fixture_hostname=os.getenv('PKGLIB_TESTING_FIXTURE_HOSTNAME', socket.gethostname()),
    java_executable=os.getenv('PKGLIB_TESTING_JAVA', "java"),
    jenkins_url=os.getenv('PKGLIB_TESTING_JENKINS_URL', 'http://acmejenkins.example.com'),
    jenkins_war=os.getenv('PKGLIB_TESTING_JENKINS_WAR', '/usr/share/jenkins/jenkins.war'),
    mongo_bin=os.getenv('PKGLIB_TESTING_MONGO_BIN', '/usr/bin'),
    redis_executable=os.getenv('PKGLIB_TESTING_REDIS', "/usr/sbin/redis-server"),
    virtualenv_executable=os.getenv('PKGLIB_TESTING_VIRTUALENV', "virtualenv"),
)
