import os

import pytest

from pkglib.testing import util

TEMP_NAME = 'JUNK123_456_789'

Shell = util.Shell
chdir = util.chdir


def test_set_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with util.set_env(TEMP_NAME, 'not_junk'):
            assert os.environ[TEMP_NAME] == 'not_junk'
        assert os.environ[TEMP_NAME] == ev
    finally:
        del os.environ[TEMP_NAME]


def test_set_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]

    with util.set_env(TEMP_NAME, 'anything'):
        assert os.environ[TEMP_NAME] == 'anything'
    assert TEMP_NAME not in os.environ


def test_unset_env():
    try:
        os.environ[TEMP_NAME] = 'junk_name'
        assert os.environ[TEMP_NAME] == 'junk_name'

        with util.unset_env([TEMP_NAME]):
            with pytest.raises(KeyError):  # @UndefinedVariable
                os.environ[TEMP_NAME]

        assert os.environ[TEMP_NAME] == 'junk_name'
    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_no_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with util.no_env(TEMP_NAME):
            assert TEMP_NAME not in os.environ
        assert os.environ[TEMP_NAME] == ev
    finally:
        del os.environ[TEMP_NAME]


def test_no_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with util.no_env(TEMP_NAME):
        assert TEMP_NAME not in os.environ
    assert TEMP_NAME not in os.environ


def test_subprocess_set_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with util.set_env(TEMP_NAME, 'anything'):
            out, _ = util.launch('env')
            for o in out.split('\n'):
                if o.startswith(TEMP_NAME):
                    assert o == '%s=anything' % TEMP_NAME
                    break
            else:
                assert False, '%s not found in os.environ' % TEMP_NAME
        assert os.environ[TEMP_NAME] == ev

    finally:
        del os.environ[TEMP_NAME]


def test_subprocess_set_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with util.set_env(TEMP_NAME, 'anything'):
        out, _ = util.launch('env')
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert o == '%s=anything' % TEMP_NAME
                break
        else:
            assert False, '%s not found in os.environ' % TEMP_NAME


def test_subprocess_no_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with util.no_env(TEMP_NAME):
            out, _ = util.launch('env')
            for o in out.split('\n'):
                if o.startswith(TEMP_NAME):
                    assert False, '%s found in os.environ' % TEMP_NAME

        assert os.environ[TEMP_NAME] == ev
    finally:
        del os.environ[TEMP_NAME]


def test_subprocess_no_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with util.no_env(TEMP_NAME):
        out, _ = util.launch('env')
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert False, '%s found in os.environ' % TEMP_NAME

    assert TEMP_NAME not in os.environ


def test_set_env_with_kwargs_updates():
    test_env = {"TESTING_A": "a",
                "TESTING_B": "b",
                "TESTING_C": "c"}
    os.environ.update(test_env)
    with util.set_env("TESTING_A", 1, TESTING_B="fred",
                      TESTING_C=None):
        assert os.environ["TESTING_A"] == "1"
        assert os.environ["TESTING_B"] == "fred"
        assert "C" not in os.environ
    assert os.environ["TESTING_A"] == "a"
    assert os.environ["TESTING_B"] == "b"
    assert os.environ["TESTING_C"] == "c"


def test_launch():
    out, _ = util.launch(['env'])
    assert 'HOME=' in out
