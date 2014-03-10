import os
from uuid import uuid4

import pytest
from mock import Mock, patch, sentinel, DEFAULT, call
from six.moves import cPickle  # @UnresolvedImport

from pkglib_testing import util

TEMP_NAME = 'JUNK123_456_789'
ARG = str(uuid4())
KW = str(uuid4())

Shell = util.Shell


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
        if TEMP_NAME in os.environ:
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
            out = util.launch('env')[0]
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
    with util.set_env(TEMP_NAME, 'anything'):
        out = util.launch('env')[0]
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
            out = util.launch('env')[0]
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
    with util.no_env(TEMP_NAME):
        out = util.launch('env')[0]
        for o in out.split('\n'):
            if o.startswith(TEMP_NAME):
                assert False, '%s found in os.environ' % TEMP_NAME

    assert TEMP_NAME not in os.environ


def test_set_env_with_kwargs_updates():
    test_env = {"TEST_ACME_TESTING_A": "a",
                "TEST_ACME_TESTING_B": "b",
                "TEST_ACME_TESTING_C": "c"}
    os.environ.update(test_env)
    with util.set_env("TEST_ACME_TESTING_A", 1, TEST_ACME_TESTING_B="fred",
                      TEST_ACME_TESTING_C=None):
        assert os.environ["TEST_ACME_TESTING_A"] == "1"
        assert os.environ["TEST_ACME_TESTING_B"] == "fred"
        assert "C" not in os.environ
    assert os.environ["TEST_ACME_TESTING_A"] == "a"
    assert os.environ["TEST_ACME_TESTING_B"] == "b"
    assert os.environ["TEST_ACME_TESTING_C"] == "c"


def test_launch():
    out, _ = util.launch(['env'])
    assert 'HOME=' in out


def test_run_in_subprocess():
    with patch.multiple('pkglib_testing.util', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        fn = Mock(__name__='fn')
        res = util.run_in_subprocess(fn, python='sentinel.python')(sentinel.arg, kw=sentinel.kw)
        mocks['execnet'].makegateway.assert_called_once_with('popen//python=sentinel.python')
        gw = mocks['execnet'].makegateway.return_value
        ((remote_fn,), _) = gw.remote_exec.call_args
        chan = gw.remote_exec.return_value
        mocks['cPickle'].dumps.assert_called_with((fn, (sentinel.arg,), {'kw': sentinel.kw}), protocol=0)
        chan.send.assert_called_with(mocks['cPickle'].dumps.return_value)
        chan.receive.assert_has_calls([call(-1) for _i in range(gw.remote_exec.call_count)])
        mocks['cPickle'].loads.assert_called_once_with(chan.receive.return_value)
        assert res is mocks['cPickle'].loads.return_value
        chan.close.assert_has_calls([call() for _i in range(gw.remote_exec.call_count)])
        gw.exit.assert_called_once_with()

    with patch('six.moves.cPickle') as cPickle:  # NOQA
        channel, fn = Mock(), Mock()
        cPickle.loads.return_value = (fn, (sentinel.arg,), {'kw': sentinel.kw})
        remote_fn(channel)
        channel.receive.assert_called_once_with(-1)
        cPickle.loads.assert_called_once_with(channel.receive.return_value)
        fn.assert_called_once_with(sentinel.arg, kw=sentinel.kw)
        cPickle.dumps.assert_called_once_with(fn.return_value, protocol=0)
        channel.send.assert_called_once_with(cPickle.dumps.return_value)


def test_run_in_subprocess_cd():
    with patch.multiple('pkglib_testing.util', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        util.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               cd='sentinel.cd')(sentinel.arg, kw=sentinel.kw)
        mocks['execnet'].makegateway.assert_called_once_with('popen//python=sentinel.python//chdir=sentinel.cd')


def test_run_in_subprocess_timeout():
    with patch.multiple('pkglib_testing.util', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        util.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               timeout=sentinel.timeout)(sentinel.arg, kw=sentinel.kw)
        gw = mocks['execnet'].makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.assert_called_with(sentinel.timeout)


def test_run_in_subprocess_pickleable_function():
    def fn(*args, **kwargs):
        return args, kwargs
    fn.__name__ = 'fn_' + str(uuid4()).replace('-', '_')
    fn.__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(util, fn.__name__, fn, create=True):
            util.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (fn, (ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_str():
    source = """def fn(*args, **kwargs):
    return args, kwargs
"""
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        util.run_in_subprocess(source, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (util._evaluate_fn_source, (source, ARG,), {'kw': KW})
        ((remote_fn,), _) = gw.remote_exec.call_args
        ((chan.receive.return_value,), _) = chan.send.call_args
        remote_fn(chan)
        chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_nested_function():
    def fn(*args, **kwargs):
        return args, kwargs
    source = """def fn(*args, **kwargs):
    return args, kwargs
"""
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        util.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (util._evaluate_fn_source, (source, ARG,), {'kw': KW})
        ((remote_fn,), _) = gw.remote_exec.call_args
        ((chan.receive.return_value,), _) = chan.send.call_args
        remote_fn(chan)
        chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_bound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(util, C.__name__, C, create=True):
            util.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (util._invoke_method, (c, 'fn', ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_bound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pkglib_testing.util.execnet'):
        with pytest.raises(cPickle.PicklingError):
            util.run_in_subprocess(C().fn, python='sentinel.python')(ARG, kw=KW)


def test_run_in_subprocess_unbound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.__dict__['fn'].__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(util, C.__name__, C, create=True):
            util.run_in_subprocess(C.fn, python='sentinel.python')(c, ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (util._invoke_method, (C, 'fn', c, ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_unbound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pkglib_testing.util.execnet'):
        with pytest.raises(cPickle.PicklingError):
            util.run_in_subprocess(C.fn, python='sentinel.python')(C(), ARG, kw=KW)


def test_run_in_subprocess_staticmethod():
    class C(object):
        @staticmethod
        def fn(*args, **kwargs):
            return args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.fn.__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(util, C.__name__, C, create=True):
            util.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (util._invoke_method, (C, 'fn', ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_staticmethod_on_unpickleable_class():
    class C(object):
        @staticmethod
        def fn(*args, **kwargs):
            return args, kwargs
    source = """@staticmethod
def fn(*args, **kwargs):
    return args, kwargs
"""
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.fn.__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(util, C.__name__, C, create=True):
            util.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (util._evaluate_fn_source, (source, ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_classmethod():
    class C(object):
        @classmethod
        def fn(cls, *args, **kwargs):
            return cls, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = 'pkglib_testing.util'
    with patch('pkglib_testing.util.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(util, C.__name__, C, create=True):
            util.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (util._invoke_method, (C, 'fn', ARG), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((C, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_classmethod_on_unpickleable_class():
    class C(object):
        @classmethod
        def fn(cls, *args, **kwargs):
            return cls, args, kwargs
    with patch('pkglib_testing.util.execnet'):
        with pytest.raises(cPickle.PicklingError):
            util.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
