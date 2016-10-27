import sys
from uuid import uuid4
from subprocess import PIPE, STDOUT

import pytest
from mock import Mock, patch, sentinel, DEFAULT, call
from six.moves import cPickle

from pytest_shutil import run

ARG = str(uuid4())
KW = str(uuid4())

def test_run_passes_stdout_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = (None, '')
        run.run(sentinel.cmd, capture_stdout=False, capture_stderr=True)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=None, stderr=STDOUT)


def test_run_passes_stderr_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = ('', None)
        run.run(sentinel.cmd, capture_stdout=True, capture_stderr=False)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=PIPE, stderr=None)


def test_run_passes_stdout_and_stderr_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = (None, None)
        run.run(sentinel.cmd, capture_stdout=False, capture_stderr=False)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=None, stderr=None)


def test_run_as_main():
    def foo():
        import sys
        assert sys.argv[1] == 'bar'
        assert sys.argv[2] == 'baz'
    run.run_as_main(foo, 'bar', 'baz')


def test_run_in_subprocess():
    with patch.multiple('pytest_shutil.run', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        fn = Mock(__name__='fn')
        res = run.run_in_subprocess(fn, python='sentinel.python')(sentinel.arg, kw=sentinel.kw)
        mocks['execnet'].makegateway.assert_called_once_with('popen//python=sentinel.python')
        gw = mocks['execnet'].makegateway.return_value
        ((remote_fn,), _) = gw.remote_exec.call_args
        chan = gw.remote_exec.return_value
        mocks['cPickle'].dumps.assert_called_with((fn, (sentinel.arg,), {'kw': sentinel.kw}), protocol=0)
        chan.send.assert_called_with(mocks['cPickle'].dumps.return_value)
        chan.receive.assert_has_calls([call(None) for _i in range(gw.remote_exec.call_count)])
        mocks['cPickle'].loads.assert_called_once_with(chan.receive.return_value)
        assert res is mocks['cPickle'].loads.return_value
        chan.close.assert_has_calls([call() for _i in range(gw.remote_exec.call_count)])
        gw.exit.assert_called_once_with()

    with patch('six.moves.cPickle') as cPickle:
        channel, fn = Mock(), Mock()
        cPickle.loads.return_value = (fn, (sentinel.arg,), {'kw': sentinel.kw})
        remote_fn(channel)
        channel.receive.assert_called_once_with(None)
        cPickle.loads.assert_called_once_with(channel.receive.return_value)
        fn.assert_called_once_with(sentinel.arg, kw=sentinel.kw)
        cPickle.dumps.assert_called_once_with(fn.return_value, protocol=0)
        channel.send.assert_called_once_with(cPickle.dumps.return_value)


def test_run_in_runcd():
    with patch.multiple('pytest_shutil.run', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        run.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               cd='sentinel.cd')(sentinel.arg, kw=sentinel.kw)
        mocks['execnet'].makegateway.assert_called_once_with('popen//python=sentinel.python//chdir=sentinel.cd')


def test_run_in_runtimeout():
    with patch.multiple('pytest_shutil.run', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        run.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               timeout=sentinel.timeout)(sentinel.arg, kw=sentinel.kw)
        gw = mocks['execnet'].makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.assert_called_with(sentinel.timeout)

@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runpickleable_function():
    def fn(*args, **kwargs):
        return args, kwargs
    fn.__name__ = 'fn_' + str(uuid4()).replace('-', '_')
    fn.__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(run, fn.__name__, fn, create=True):
            run.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (fn, (ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_runstr():
    source = """def fn(*args, **kwargs):
    return args, kwargs
"""
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        run.run_in_subprocess(source, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (run._evaluate_fn_source, (source, ARG,), {'kw': KW})
        ((remote_fn,), _) = gw.remote_exec.call_args
        ((chan.receive.return_value,), _) = chan.send.call_args
        remote_fn(chan)
        chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_runnested_function():
    def fn(*args, **kwargs):
        return args, kwargs
    source = """def fn(*args, **kwargs):
    return args, kwargs
"""
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        run.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (run._evaluate_fn_source, (source, ARG,), {'kw': KW})
        ((remote_fn,), _) = gw.remote_exec.call_args
        ((chan.receive.return_value,), _) = chan.send.call_args
        remote_fn(chan)
        chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runbound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(run, C.__name__, C, create=True):
            run.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args

            if sys.version_info < (3, 0, 0):
                # Bound methods are not pickleable in Python 2.
                assert cPickle.loads(s) == (run._invoke_method, (c, 'fn', ARG,), {'kw': KW})
            else:
                # Bound methods are pickleable in Python 3.
                assert cPickle.loads(s) == (c.fn, (ARG,), {'kw': KW})

            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runbound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pytest_shutil.run.execnet'):
        with pytest.raises(cPickle.PicklingError):
            run.run_in_subprocess(C().fn, python='sentinel.python')(ARG, kw=KW)


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_rununbound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.__dict__['fn'].__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(run, C.__name__, C, create=True):
            run.run_in_subprocess(C.fn, python='sentinel.python')(c, ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (run._invoke_method, (C, 'fn', c, ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_rununbound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pytest_shutil.run.execnet'):
        with pytest.raises(cPickle.PicklingError):
            run.run_in_subprocess(C.fn, python='sentinel.python')(C(), ARG, kw=KW)


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runstaticmethod():
    class C(object):
        @staticmethod
        def fn(*args, **kwargs):
            return args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.fn.__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(run, C.__name__, C, create=True):
            run.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (run._invoke_method, (C, 'fn', ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runstaticmethod_on_unpickleable_class():
    class C(object):
        @staticmethod
        def fn(*args, **kwargs):
            return args, kwargs
    source = """@staticmethod
def fn(*args, **kwargs):
    return args, kwargs
"""
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.fn.__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(run, C.__name__, C, create=True):
            run.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (run._evaluate_fn_source, (source, ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runclassmethod():
    class C(object):
        @classmethod
        def fn(cls, *args, **kwargs):
            return cls, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = 'pytest_shutil.run'
    with patch('pytest_shutil.run.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(run, C.__name__, C, create=True):
            run.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            if sys.version_info < (3, 0, 0):
                # Class methods are not pickleable in Python 2.
                assert cPickle.loads(s) == (run._invoke_method, (C, 'fn', ARG), {'kw': KW})
            else:
                # Class methods are pickleable in Python 3.
                assert cPickle.loads(s) == (c.fn, (ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((C, (ARG,), {'kw': KW}), protocol=0))


@pytest.mark.xfail(sys.version_info >= (3,5), reason="python3.5 api changes")
def test_run_in_runclassmethod_on_unpickleable_class():
    class C(object):
        @classmethod
        def fn(cls, *args, **kwargs):
            return cls, args, kwargs
    with patch('pytest_shutil.run.execnet'):
        with pytest.raises(cPickle.PicklingError):
            run.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
