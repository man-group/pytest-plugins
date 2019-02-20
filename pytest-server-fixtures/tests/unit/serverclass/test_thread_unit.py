from mock import sentinel, patch, Mock

from pytest_server_fixtures import CONFIG
from pytest_server_fixtures.serverclass.thread import ThreadServer


@patch('pytest_server_fixtures.serverclass.thread.ServerClass.__init__')
def test_init(mock_init):
    ts = ThreadServer(sentinel.cmd,
                      sentinel.get_args,
                      sentinel.env,
                      sentinel.workspace,
                      cwd=sentinel.cwd,
                      listen_hostname=sentinel.listen_hostname)

    mock_init.assert_called_with(sentinel.cmd,
                                 sentinel.get_args,
                                 sentinel.env)
    assert ts._hostname == sentinel.listen_hostname
    assert ts._workspace == sentinel.workspace
    assert ts._cwd == sentinel.cwd

