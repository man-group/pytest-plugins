try:
    from unittest.mock import create_autospec, sentinel, call, patch, Mock
except ImportError:
    # python 2
    from mock import create_autospec, sentinel, call, patch, Mock

from pytest_server_fixtures.base import TestServer as _TestServer  # So that pytest doesnt think this is a test case


def test_init():
    ws = Mock()
    with patch('pytest_shutil.workspace.Workspace.__init__', autospec=True) as init:
        ts = _TestServer(workspace=ws, delete=sentinel.delete,
                         port=sentinel.port, hostname=sentinel.hostname)
    assert init.call_args_list == [call(ts, workspace=ws, delete=sentinel.delete)]
    assert ts.hostname == sentinel.hostname
    assert ts.port == sentinel.port
    assert ts.dead is False

    # Silence teardown warnings
    ts.dead = True
    ts.workspace = ws


def test_kill_by_port():
    server = _TestServer(hostname=sentinel.hostname, port=sentinel.port)
    server.run = Mock(side_effect=['100\n', '', ''])
    server._signal = Mock()
    with patch('socket.gethostbyname', return_value=sentinel.ip):
        server._find_and_kill_by_port(2, sentinel.signal)
        server.dead = True
    assert server.run.call_args_list == [call("netstat -anp 2>/dev/null | grep sentinel.ip:sentinel.port "
                                            "| grep LISTEN | awk '{ print $7 }' | cut -d'/' -f1", capture=True, cd='/'),
                                       call("netstat -anp 2>/dev/null | grep sentinel.ip:sentinel.port "
                                            "| grep LISTEN | awk '{ print $7 }' | cut -d'/' -f1", capture=True, cd='/')]
    assert server._signal.call_args_list == [call(100, sentinel.signal)]
