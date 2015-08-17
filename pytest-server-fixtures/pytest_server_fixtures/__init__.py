import socket
import os

from pytest_fixture_config import Config


class FixtureConfig(Config):
    __slots__ = ('java_executable', 'jenkins_url', 'jenkins_war', 'mongo_bin', 'redis_executable',
                 'rethink_executable', 'httpd_executable', 'httpd_modules', 'fixture_hostname')

# Global config for finding system resources.
CONFIG = FixtureConfig(
    # Not using localhost here in case we are being used in a cluster-type job
    fixture_hostname=os.getenv('SERVER_FIXTURES_HOSTNAME', socket.gethostname()),
    java_executable=os.getenv('SERVER_FIXTURES_JAVA', "java"),
    jenkins_url=os.getenv('SERVER_FIXTURES_JENKINS_URL', 'http://acmejenkins.example.com'),
    jenkins_war=os.getenv('SERVER_FIXTURES_JENKINS_WAR', '/usr/share/jenkins/jenkins.war'),
    mongo_bin=os.getenv('SERVER_FIXTURES_MONGO_BIN', '/usr/bin'),
    redis_executable=os.getenv('SERVER_FIXTURES_REDIS', "/usr/sbin/redis-server"),
    rethink_executable=os.getenv('SERVER_FIXTURES_RETHINK', "/usr/bin/rethinkdb"),
    httpd_executable=os.getenv('SERVER_FIXTURES_HTTPD', "/usr/sbin/apache2"),
    httpd_modules=os.getenv('SERVER_FIXTURES_HTTPD_MODULES', "/usr/lib/apache2/modules"),
)
