import os

from pytest_shutil import env, run

TEMP_NAME = 'JUNK123_456_789'

def test_set_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with env.set_env(TEMP_NAME, 'anything'):
            out = run.run('env', capture_stdout=True)
            for o in out.split('\n'):
                if o.startswith(TEMP_NAME):
                    assert o == '%s=anything' % TEMP_NAME
                    break
            else:
                assert False, '%s not found in os.environ' % TEMP_NAME
        assert os.environ[TEMP_NAME] == ev

    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_set_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with env.set_env(TEMP_NAME, 'anything'):
        out = run.run('env', capture_stdout=True)
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert o == '%s=anything' % TEMP_NAME
                break
        else:
            assert False, '%s not found in os.environ' % TEMP_NAME


def test_subprocecmdline():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with env.no_env(TEMP_NAME):
            out = run.run('env', capture_stdout=True)
            for o in out.split('\n'):
                if o.startswith(TEMP_NAME):
                    assert False, '%s found in os.environ' % TEMP_NAME

        assert os.environ[TEMP_NAME] == ev
    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_no_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with env.no_env(TEMP_NAME):
        out = run.run('env', capture_stdout=True)
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert False, '%s found in os.environ' % TEMP_NAME

    assert TEMP_NAME not in os.environ
