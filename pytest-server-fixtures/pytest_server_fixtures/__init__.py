import socket
import os

from pytest_fixture_config import Config


class FixtureConfig(Config):
    __slots__ = ('java_executable', 'jenkins_url', 'jenkins_war', 'minio_executable', 'mongo_bin', 'redis_executable',
                 'rethink_executable', 'httpd_executable', 'httpd_modules', 'fixture_hostname',
                 'xvfb_executable', 'disable_proxy', 'driver', 'mongo_docker_image')

# Default values for system resource locations - patch this to change defaults
DEFAULT_SERVER_FIXTURES_HOSTNAME = socket.gethostname()
DEFAULT_SERVER_FIXTURES_DISABLE_HTTP_PROXY = True
DEFAULT_SERVER_FIXTURES_DRIVER = "local"
DEFAULT_SERVER_FIXTURES_JAVA = "java"
DEFAULT_SERVER_FIXTURES_JENKINS_URL = 'http://acmejenkins.example.com'
DEFAULT_SERVER_FIXTURES_JENKINS_WAR = '/usr/share/jenkins/jenkins.war'
DEFAULT_SERVER_FIXTURES_MINIO = '/usr/local/bin/minio'
DEFAULT_SERVER_FIXTURES_MONGO_BIN = ''
DEFAULT_SERVER_FIXTURES_MONGO_DOCKER_IMAGE = "mongo:3.6"
DEFAULT_SERVER_FIXTURES_REDIS = "/usr/bin/redis-server"
DEFAULT_SERVER_FIXTURES_RETHINK = "/usr/bin/rethinkdb"
DEFAULT_SERVER_FIXTURES_HTTPD = "/usr/sbin/apache2"
DEFAULT_SERVER_FIXTURES_HTTPD_MODULES = "/usr/lib/apache2/modules"
DEFAULT_SERVER_FIXTURES_XVFB = "/usr/bin/Xvfb"


# Global config for finding system resources.
CONFIG = FixtureConfig(
    # Not using localhost here in case we are being used in a cluster-type job
    fixture_hostname=os.getenv('SERVER_FIXTURES_HOSTNAME', DEFAULT_SERVER_FIXTURES_HOSTNAME),
    disable_proxy=os.getenv('SERVER_FIXTURES_DISABLE_HTTP_PROXY', DEFAULT_SERVER_FIXTURES_DISABLE_HTTP_PROXY),
    driver=os.getenv('SERVER_FIXTURES_DRIVER', DEFAULT_SERVER_FIXTURES_DRIVER),
    java_executable=os.getenv('SERVER_FIXTURES_JAVA', DEFAULT_SERVER_FIXTURES_JAVA),
    jenkins_war=os.getenv('SERVER_FIXTURES_JENKINS_WAR', DEFAULT_SERVER_FIXTURES_JENKINS_WAR),
    minio_executable=os.getenv('SERVER_FIXTURES_MINIO', DEFAULT_SERVER_FIXTURES_MINIO),
    mongo_bin=os.getenv('SERVER_FIXTURES_MONGO_BIN', DEFAULT_SERVER_FIXTURES_MONGO_BIN),
    mongo_docker_image=os.getenv('SERVER_FIXTURES_MONGO_DOCKER_IMAGE', DEFAULT_SERVER_FIXTURES_MONGO_DOCKER_IMAGE),
    redis_executable=os.getenv('SERVER_FIXTURES_REDIS', DEFAULT_SERVER_FIXTURES_REDIS),
    rethink_executable=os.getenv('SERVER_FIXTURES_RETHINK', DEFAULT_SERVER_FIXTURES_RETHINK),
    httpd_executable=os.getenv('SERVER_FIXTURES_HTTPD', DEFAULT_SERVER_FIXTURES_HTTPD),
    httpd_modules=os.getenv('SERVER_FIXTURES_HTTPD_MODULES', DEFAULT_SERVER_FIXTURES_HTTPD_MODULES),
    xvfb_executable=os.getenv('SERVER_FIXTURES_XVFB', DEFAULT_SERVER_FIXTURES_XVFB),
)
