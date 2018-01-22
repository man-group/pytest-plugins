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


def test_kill():
    self = create_autospec(_TestServer, dead=False,
                           hostname=sentinel.hostname,
                           port=sentinel.port)
    self.run.side_effect = ['100\n', '', '']
    with patch('os.kill') as kill:
        with patch('socket.gethostbyname', return_value=sentinel.ip):
            _TestServer._find_and_kill(self, 2, sentinel.signal)
    assert self.run.call_args_list == [call("netstat -anp 2>/dev/null | grep sentinel.ip:sentinel.port "
                                            "| grep LISTEN | awk '{ print $7 }' | cut -d'/' -f1", capture=True, cd='/'),
                                       call("netstat -anp 2>/dev/null | grep sentinel.ip:sentinel.port "
                                            "| grep LISTEN | awk '{ print $7 }' | cut -d'/' -f1", capture=True, cd='/')]
    assert kill.call_args_list == [call(100, sentinel.signal)]
