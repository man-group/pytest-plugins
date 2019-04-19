import pytest

from mock import sentinel, patch, Mock

from pytest_server_fixtures.serverclass.kubernetes import KubernetesServer

@pytest.mark.skip(reason="Need a way to run this test in Kubernetes")
@patch('pytest_server_fixtures.serverclass.docker.ServerClass.__init__')
def test_init(mock_init):
    s = KubernetesServer(sentinel.server_type,
                         sentinel.cmd,
                         sentinel.get_args,
                         sentinel.env,
                         sentinel.image)

    mock_init.assert_called_with(sentinel.cmd,
                                 sentinel.get_args,
                                 sentinel.env)

