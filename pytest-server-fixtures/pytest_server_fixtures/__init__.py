import socket
import os

from pytest_fixture_config import Config


class FixtureConfig(Config):
    __slots__ = (
        'java_executable',
        'jenkins_url',
        'jenkins_war',
        'jenkins_image'
        'minio_executable',
        'minio_image',
        'mongo_bin',
        'mongo_image',
        'postgres_image',
        'redis_executable',
        'redis_image',
        'rethink_executable',
        'rethink_image',
        'httpd_executable',
        'httpd_image',
        'httpd_modules',
        'fixture_hostname',
        'xvfb_executable',
        'disable_proxy',
        'server_class',
    )

# Default values for system resource locations - patch this to change defaults
DEFAULT_SERVER_FIXTURES_HOSTNAME = socket.gethostname()
DEFAULT_SERVER_FIXTURES_DISABLE_HTTP_PROXY = True
DEFAULT_SERVER_FIXTURES_SERVER_CLASS = 'docker'
DEFAULT_SERVER_FIXTURES_JAVA = 'java'
DEFAULT_SERVER_FIXTURES_JENKINS_URL = 'http://acmejenkins.example.com'
DEFAULT_SERVER_FIXTURES_JENKINS_WAR = '/usr/share/jenkins/jenkins.war'
DEFAULT_SERVER_FIXTURES_JENKINS_IMAGE = 'jenkins/jenkins:2.138.3-alpine'
DEFAULT_SERVER_FIXTURES_MINIO = '/usr/local/bin/minio'
DEFAULT_SERVER_FIXTURES_MINIO_IMAGE = 'minio/minio:latest'
DEFAULT_SERVER_FIXTURES_MONGO_BIN = ''
DEFAULT_SERVER_FIXTURES_MONGO_IMAGE = 'mongo:3.6'
DEFAULT_SERVER_FIXTURES_POSTGRES_IMAGE = 'postgres:11.1'
DEFAULT_SERVER_FIXTURES_REDIS = '/usr/bin/redis-server'
DEFAULT_SERVER_FIXTURES_REDIS_IMAGE = 'redis:5.0.1-alpine'
DEFAULT_SERVER_FIXTURES_RETHINK = '/usr/bin/rethinkdb'
DEFAULT_SERVER_FIXTURES_RETHINK_IMAGE = 'rethink:2.3.6'
DEFAULT_SERVER_FIXTURES_HTTPD = '/usr/sbin/apache2'
DEFAULT_SERVER_FIXTURES_HTTPD_IMAGE = 'httpd:2.4.37'
DEFAULT_SERVER_FIXTURES_HTTPD_MODULES = '/usr/lib/apache2/modules'
DEFAULT_SERVER_FIXTURES_XVFB = '/usr/bin/Xvfb'


# Global config for finding system resources.
CONFIG = FixtureConfig(
    # Not using localhost here in case we are being used in a cluster-type job
    fixture_hostname=os.getenv('SERVER_FIXTURES_HOSTNAME', DEFAULT_SERVER_FIXTURES_HOSTNAME),
    disable_proxy=os.getenv('SERVER_FIXTURES_DISABLE_HTTP_PROXY', DEFAULT_SERVER_FIXTURES_DISABLE_HTTP_PROXY),
    server_class=os.getenv('SERVER_FIXTURES_SERVER_CLASS', DEFAULT_SERVER_FIXTURES_SERVER_CLASS),
    java_executable=os.getenv('SERVER_FIXTURES_JAVA', DEFAULT_SERVER_FIXTURES_JAVA),
    jenkins_war=os.getenv('SERVER_FIXTURES_JENKINS_WAR', DEFAULT_SERVER_FIXTURES_JENKINS_WAR),
    jenkins_image=os.getenv('SERVER_FIXTURES_JENKINS_IMAGE', DEFAULT_SERVER_FIXTURES_JENKINS_IMAGE),
    minio_executable=os.getenv('SERVER_FIXTURES_MINIO', DEFAULT_SERVER_FIXTURES_MINIO),
    minio_image=os.getenv('SERVER_FIXTURES_MINIO_IMAGE', DEFAULT_SERVER_FIXTURES_MINIO_IMAGE),
    mongo_bin=os.getenv('SERVER_FIXTURES_MONGO_BIN', DEFAULT_SERVER_FIXTURES_MONGO_BIN),
    mongo_image=os.getenv('SERVER_FIXTURES_MONGO_IMAGE', DEFAULT_SERVER_FIXTURES_MONGO_IMAGE),
    postgres_image=os.getenv('SERVER_FIXTURES_POSTGRES_IMAGE', DEFAULT_SERVER_FIXTURES_POSTGRES_IMAGE),
    redis_executable=os.getenv('SERVER_FIXTURES_REDIS', DEFAULT_SERVER_FIXTURES_REDIS),
    redis_image=os.getenv('SERVER_FIXTURES_REDIS_IMAGE', DEFAULT_SERVER_FIXTURES_REDIS_IMAGE),
    rethink_executable=os.getenv('SERVER_FIXTURES_RETHINK', DEFAULT_SERVER_FIXTURES_RETHINK),
    rethink_image=os.getenv('SERVER_FIXTURES_RETHINK_IMAGE', DEFAULT_SERVER_FIXTURES_RETHINK_IMAGE),
    httpd_executable=os.getenv('SERVER_FIXTURES_HTTPD', DEFAULT_SERVER_FIXTURES_HTTPD),
    httpd_modules=os.getenv('SERVER_FIXTURES_HTTPD_MODULES', DEFAULT_SERVER_FIXTURES_HTTPD_MODULES),
    httpd_image=os.getenv('SERVER_FIXTURES_HTTPD_IMAGE', DEFAULT_SERVER_FIXTURES_HTTPD_IMAGE),
    xvfb_executable=os.getenv('SERVER_FIXTURES_XVFB', DEFAULT_SERVER_FIXTURES_XVFB),
)
