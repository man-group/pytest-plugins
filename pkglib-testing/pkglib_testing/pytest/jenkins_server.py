import pytest

from pkglib_testing.jenkins_server import JenkinsTestServer
from util import requires_config


@requires_config(['jenkins_war', 'java_executable'])
@pytest.yield_fixture(scope='session')
def jenkins_server():
    """ Boot up Jenkins in a local thread.
        This also provides a temp workspace.
    """
    with JenkinsTestServer() as p:
        p.start()
        yield p
