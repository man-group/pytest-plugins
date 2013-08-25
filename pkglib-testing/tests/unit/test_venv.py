import mock

import pkglib_testing.util as util


def test_PYTHONPATH_not_present_in_testing_env_if_set():
    with util.set_env('PYTHONPATH', 'fred'):
        with mock.patch.object(util.Workspace, 'run') as run:
            util.TmpVirtualEnv()
            call = run.mock_calls[0]
            assert 'PYTHONPATH' not in call[2]['env']

            util.TmpVirtualEnv({'PYTHONPATH': 'john'})
            call = run.mock_calls[1]
            assert 'PYTHONPATH' not in call[2]['env']


def test_PYTHONPATH_not_present_in_testing_env_if_unset():
    with util.no_env('PYTHONPATH'):
        with mock.patch.object(util.Workspace, 'run') as run:
            util.TmpVirtualEnv()
            call = run.mock_calls[0]
            assert 'PYTHONPATH' not in call[2]['env']

            util.TmpVirtualEnv({'PYTHONPATH': 'john'})
            call = run.mock_calls[1]
            assert 'PYTHONPATH' not in call[2]['env']
