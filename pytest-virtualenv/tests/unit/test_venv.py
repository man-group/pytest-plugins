import mock

import pytest_virtualenv as venv
from pytest_shutil import env


def test_PYTHONPATH_not_present_in_testing_env_if_set():
    with env.set_env('PYTHONPATH', 'fred'):
        with mock.patch.object(venv.Workspace, 'run') as run:
            venv.VirtualEnv()
            call = run.mock_calls[0]
            assert 'PYTHONPATH' not in call[2]['env']

            venv.VirtualEnv({'PYTHONPATH': 'john'})
            call = run.mock_calls[1]
            assert 'PYTHONPATH' not in call[2]['env']


def test_PYTHONPATH_not_present_in_testing_env_if_unset():
    with env.no_env('PYTHONPATH'):
        with mock.patch.object(venv.Workspace, 'run') as run:
            venv.VirtualEnv()
            call = run.mock_calls[0]
            assert 'PYTHONPATH' not in call[2]['env']

            venv.VirtualEnv({'PYTHONPATH': 'john'})
            call = run.mock_calls[1]
            assert 'PYTHONPATH' not in call[2]['env']
