import os
from uuid import uuid4

import pytest
from pkglib_util.six.moves import cPickle

from pkglib_testing import env, cmdline

TEMP_NAME = 'JUNK123_456_789'
ARG = str(uuid4())
KW = str(uuid4())

Shell = cmdline.Shell


def test_set_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with env.set_env(TEMP_NAME, 'not_junk'):
            assert os.environ[TEMP_NAME] == 'not_junk'
        assert os.environ[TEMP_NAME] == ev
    finally:
        del os.environ[TEMP_NAME]


def test_set_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]

    with env.set_env(TEMP_NAME, 'anything'):
        assert os.environ[TEMP_NAME] == 'anything'
    assert TEMP_NAME not in os.environ


def test_unset_env():
    try:
        os.environ[TEMP_NAME] = 'junk_name'
        assert os.environ[TEMP_NAME] == 'junk_name'

        with env.unset_env([TEMP_NAME]):
            with pytest.raises(KeyError):  # @UndefinedVariable
                os.environ[TEMP_NAME]

        assert os.environ[TEMP_NAME] == 'junk_name'
    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_no_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with env.no_env(TEMP_NAME):
            assert TEMP_NAME not in os.environ
        assert os.environ[TEMP_NAME] == ev
    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_no_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with env.no_env(TEMP_NAME):
        assert TEMP_NAME not in os.environ
    assert TEMP_NAME not in os.environ


def test_subprocess_set_env_ok_if_exists():
    ev = os.environ[TEMP_NAME] = 'junk_name'
    try:
        with env.set_env(TEMP_NAME, 'anything'):
            out = cmdline.launch('env')[0]
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


def test_subprocess_set_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with env.set_env(TEMP_NAME, 'anything'):
        out = cmdline.launch('env')[0]
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
            out = cmdline.launch('env')[0]
            for o in out.split('\n'):
                if o.startswith(TEMP_NAME):
                    assert False, '%s found in os.environ' % TEMP_NAME

        assert os.environ[TEMP_NAME] == ev
    finally:
        if TEMP_NAME in os.environ:
            del os.environ[TEMP_NAME]


def test_subprocess_no_env_ok_if_not_exists():
    if TEMP_NAME in os.environ:
        del os.environ[TEMP_NAME]
    with env.no_env(TEMP_NAME):
        out = cmdline.launch('env')[0]
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert False, '%s found in os.environ' % TEMP_NAME

    assert TEMP_NAME not in os.environ


def test_set_env_with_kwargs_updates():
    test_env = {"TEST_ACME_TESTING_A": "a",
                "TEST_ACME_TESTING_B": "b",
                "TEST_ACME_TESTING_C": "c"}
    os.environ.update(test_env)
    with env.set_env("TEST_ACME_TESTING_A", 1, TEST_ACME_TESTING_B="fred",
                      TEST_ACME_TESTING_C=None):
        assert os.environ["TEST_ACME_TESTING_A"] == "1"
        assert os.environ["TEST_ACME_TESTING_B"] == "fred"
        assert "C" not in os.environ
    assert os.environ["TEST_ACME_TESTING_A"] == "a"
    assert os.environ["TEST_ACME_TESTING_B"] == "b"
    assert os.environ["TEST_ACME_TESTING_C"] == "c"



