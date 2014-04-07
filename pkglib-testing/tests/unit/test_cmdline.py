import os
from uuid import uuid4

import pytest
from mock import Mock, patch, sentinel, DEFAULT, call
from pkglib_util.six.moves import cPickle
from pkglib_util.cmdline import chdir

from pkglib_testing import cmdline
from pkglib_testing.fixtures.workspace import Workspace

TEMP_NAME = 'JUNK123_456_789'
ARG = str(uuid4())
KW = str(uuid4())


def test_run_as_main():
    def foo():
        import sys
        assert sys.argv[1] == 'bar'
        assert sys.argv[2] == 'baz'
    cmdline.run_as_main(foo, 'bar', 'baz')


def test_launch():
    out, _ = cmdline.launch(['env'])
    assert 'HOME=' in out


def test_Shell_func_1():
    with chdir(os.path.dirname(__file__)):
        with cmdline.Shell('ls') as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_Shell_func_1_as_list():
    with chdir(os.path.dirname(__file__)):
        with cmdline.Shell(['ls']) as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_Shell_func_2():
    this_dir = os.path.dirname(__file__)
    # start at parent of this directory
    with chdir(os.path.dirname(this_dir)):
        with cmdline.Shell(['cd %s' % this_dir, 'ls']) as s:
            assert os.path.basename(__file__) in s.out.split('\n')


def test_adir_is_not_present_in_initial_state_ok():
    with Workspace() as w:
        # confirm that there is no adir directory
        with cmdline.Shell(['cd %s' % w.workspace,
                                    'stat adir']
                                   ) as sh:
            sh.print_io()
            assert sh.err.strip().startswith("stat: cannot stat `adir':"), 'adir directory not absent!'


def test_mkdir_adir_stats_ok():
    with Workspace() as w:
        with cmdline.Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'stat adir']
                                   ) as sh:
            assert sh.out.strip().startswith('File: '), 'adir directory is absent'


def test_mkdir_adir_stats_abs_ok():
    with Workspace() as w:
        with cmdline.Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'stat %s/adir' % w.workspace]
                                   ) as sh:
            assert sh.out.strip().startswith('File: '), 'adir directory is absent'


def test_mkdir_with_abs_cd_works_ok():
    with Workspace() as w:
        with cmdline.Shell(['cd %s' % w.workspace,
                                    'mkdir adir',
                                    'cd %s/adir' % w.workspace,
                                    'pwd'
                                   ]) as sh:

            assert sh.out.strip().endswith('/adir'), 'adir directory is absent'


def test_mkdir_with_relative_cd_ok():
    with Workspace() as w:
        with cmdline.Shell(['cd %s' % w.workspace,
                    'mkdir adir',
                    'cd adir',
                    'pwd'
                     ]) as sh:
            sh.print_io()
            lines = sh.out.strip().split('\n')
            assert len(lines) == 1
            assert lines[0] == os.path.join(w.workspace, 'adir')


def test_shell_exception_ok():
    # TODO: this is brittle, diff output on diff OS
    with cmdline.Shell(['junk_command']) as sh:
        assert 'not found' in sh.err.strip()




def test_run_in_subprocess():
    with patch.multiple('pkglib_testing.cmdline', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        fn = Mock(__name__='fn')
        res = cmdline.run_in_subprocess(fn, python='sentinel.python')(sentinel.arg, kw=sentinel.kw)
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

    with patch('pkglib_util.six.moves.cPickle') as cPickle:
        channel, fn = Mock(), Mock()
        cPickle.loads.return_value = (fn, (sentinel.arg,), {'kw': sentinel.kw})
        remote_fn(channel)
        channel.receive.assert_called_once_with(None)
        cPickle.loads.assert_called_once_with(channel.receive.return_value)
        fn.assert_called_once_with(sentinel.arg, kw=sentinel.kw)
        cPickle.dumps.assert_called_once_with(fn.return_value, protocol=0)
        channel.send.assert_called_once_with(cPickle.dumps.return_value)


def test_run_in_subprocess_cd():
    with patch.multiple('pkglib_testing.cmdline', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        cmdline.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               cd='sentinel.cd')(sentinel.arg, kw=sentinel.kw)
        mocks['execnet'].makegateway.assert_called_once_with('popen//python=sentinel.python//chdir=sentinel.cd')


def test_run_in_subprocess_timeout():
    with patch.multiple('pkglib_testing.cmdline', cPickle=DEFAULT, execnet=DEFAULT) as mocks:
        cmdline.run_in_subprocess(Mock(__name__='fn'), python='sentinel.python',
                               timeout=sentinel.timeout)(sentinel.arg, kw=sentinel.kw)
        gw = mocks['execnet'].makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.assert_called_with(sentinel.timeout)


def test_run_in_subprocess_pickleable_function():
    def fn(*args, **kwargs):
        return args, kwargs
    fn.__name__ = 'fn_' + str(uuid4()).replace('-', '_')
    fn.__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(cmdline, fn.__name__, fn, create=True):
            cmdline.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
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
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        cmdline.run_in_subprocess(source, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (cmdline._evaluate_fn_source, (source, ARG,), {'kw': KW})
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
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        cmdline.run_in_subprocess(fn, python='sentinel.python')(ARG, kw=KW)
        ((s,), _) = chan.send.call_args
        assert cPickle.loads(s) == (cmdline._evaluate_fn_source, (source, ARG,), {'kw': KW})
        ((remote_fn,), _) = gw.remote_exec.call_args
        ((chan.receive.return_value,), _) = chan.send.call_args
        remote_fn(chan)
        chan.send.assert_called_with(cPickle.dumps(((ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_bound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(cmdline, C.__name__, C, create=True):
            cmdline.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (cmdline._invoke_method, (c, 'fn', ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_bound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pkglib_testing.cmdline.execnet'):
        with pytest.raises(cPickle.PicklingError):
            cmdline.run_in_subprocess(C().fn, python='sentinel.python')(ARG, kw=KW)


def test_run_in_subprocess_unbound_method():
    class C(tuple):  # for equality of instances
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.__dict__['fn'].__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(cmdline, C.__name__, C, create=True):
            cmdline.run_in_subprocess(C.fn, python='sentinel.python')(c, ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (cmdline._invoke_method, (C, 'fn', c, ARG,), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((c, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_unbound_method_on_unpickleable_class():
    class C(object):
        def fn(self, *args, **kwargs):
            return self, args, kwargs
    with patch('pkglib_testing.cmdline.execnet'):
        with pytest.raises(cPickle.PicklingError):
            cmdline.run_in_subprocess(C.fn, python='sentinel.python')(C(), ARG, kw=KW)


def test_run_in_subprocess_staticmethod():
    class C(object):
        @staticmethod
        def fn(*args, **kwargs):
            return args, kwargs
    C.__name__ = 'C_' + str(uuid4()).replace('-', '_')
    C.__module__ = C.fn.__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(cmdline, C.__name__, C, create=True):
            cmdline.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (cmdline._invoke_method, (C, 'fn', ARG,), {'kw': KW})
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
    C.fn.__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        with patch.object(cmdline, C.__name__, C, create=True):
            cmdline.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (cmdline._evaluate_fn_source, (source, ARG,), {'kw': KW})
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
    C.__module__ = 'pkglib_testing.cmdline'
    with patch('pkglib_testing.cmdline.execnet') as execnet:
        gw = execnet.makegateway.return_value
        chan = gw.remote_exec.return_value
        chan.receive.return_value = cPickle.dumps(sentinel.ret)
        c = C()
        with patch.object(cmdline, C.__name__, C, create=True):
            cmdline.run_in_subprocess(c.fn, python='sentinel.python')(ARG, kw=KW)
            ((s,), _) = chan.send.call_args
            assert cPickle.loads(s) == (cmdline._invoke_method, (C, 'fn', ARG), {'kw': KW})
            ((remote_fn,), _) = gw.remote_exec.call_args
            ((chan.receive.return_value,), _) = chan.send.call_args
            remote_fn(chan)
            chan.send.assert_called_with(cPickle.dumps((C, (ARG,), {'kw': KW}), protocol=0))


def test_run_in_subprocess_classmethod_on_unpickleable_class():
    class C(object):
        @classmethod
        def fn(cls, *args, **kwargs):
            return cls, args, kwargs
    with patch('pkglib_testing.cmdline.execnet'):
        with pytest.raises(cPickle.PicklingError):
            cmdline.run_in_subprocess(C.fn, python='sentinel.python')(ARG, kw=KW)
