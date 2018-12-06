from mock import create_autospec, sentinel, call, patch, Mock

from pytest_server_fixtures.base2 import TestServerV2 as _TestServerV2 # TODO: why as _TestServerV2?


def test_init():
    ws = Mock()
    with patch('pytest_shutil.workspace.Workspace.__init__', autospec=True) as init:
        ts = _TestServerV2(delete=sentinel.delete, workspace=ws)
        assert init.call_args_list == [call(ts, workspace=ws, delete=sentinel.delete)]

