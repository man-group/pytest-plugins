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
                      random_hostname=False)

    mock_init.assert_called_with(sentinel.cmd,
                                 sentinel.get_args,
                                 sentinel.env)
    assert ts._workspace == sentinel.workspace
    assert ts._cwd == sentinel.cwd


@patch('pytest_server_fixtures.serverclass.thread.get_ephemeral_host', return_value=sentinel.host)
def test_init_with_random_hostname(mock_get_ephemeral_host):
    ts = ThreadServer(sentinel.cmd,
                      sentinel.get_args,
                      sentinel.env,
                      sentinel.workspace,
                      cwd=sentinel.cwd,
                      random_hostname=True)

    mock_get_ephemeral_host.assert_called_once()
    assert ts.hostname == sentinel.host


@patch('pytest_server_fixtures.serverclass.thread.get_ephemeral_host')
def test_init_without_random_hostname(mock_get_ephemeral_host):
    ts = ThreadServer(sentinel.cmd,
                      sentinel.get_args,
                      sentinel.env,
                      sentinel.workspace,
                      cwd=sentinel.cwd,
                      random_hostname=False)

    mock_get_ephemeral_host.assert_not_called()
    assert ts.hostname == CONFIG.fixture_hostname


