import pytest

from pkglib_testing.jenkins_server import JenkinsTestServer
from util import requires_config


@requires_config(['jenkins_war', 'java_executable'])
@pytest.fixture(scope='session')
def jenkins_server(request):
    """ Boot up Jenkins in a local thread.
        This also provides a temp workspace.
    """
    server = JenkinsTestServer()
    request.addfinalizer(lambda: server.teardown())
    server.start()
    return server
