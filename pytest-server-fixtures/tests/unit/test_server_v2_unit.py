from mock import create_autospec, sentinel, call, patch, Mock

from pytest_server_fixtures.base2 import TestServerV2 as _TestServerV2 # TODO: why as _TestServerV2?

def test_init():
    with patch('pytest_shutil.workspace.Workspace.__init__', autospec=True) as init:
        ts = _TestServerV2(cwd=sentinel.cwd,
                           workspace=sentinel.workspace,
                           delete=sentinel.delete,
                           server_class=sentinel.server_class)
        assert init.call_args_list == [call(ts, workspace=sentinel.workspace, delete=sentinel.delete)]
        assert ts._cwd == sentinel.cwd
        assert ts._server_class == sentinel.server_class

def test_hostname_when_server_is_not_started():
    ts = _TestServerV2()
    assert ts.hostname == None

