"""
    Testing tools for running cmdline methods
"""
import sys
import os
import getpass
import imp
import tempfile
from functools import update_wrapper
import inspect
import textwrap
from contextlib import contextmanager, closing
from subprocess import Popen, PIPE

from mock import patch
import execnet

from pkglib_util.six import string_types
from pkglib_util.six.moves import cPickle  # @UnresolvedImport

try:
    # Python 3
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


def run_as_main(fn, *argv):
    """ Run a given function as if it was the system entry point,
        eg for testing scripts.

    Eg::

        from scripts.Foo import main

        run_as_main(main, 'foo','bar')

    This is equivalent to ``Foo foo bar``, assuming
    ``scripts.Foo.main`` is registered as an entry point.
    """
    with patch("sys.argv", new=['progname'] + list(argv)):
        print("run_as_main: %s" % str(argv))
        fn()


def run_module_as_main(module, argv=[]):
    """ Run a given module as if it was the system entry point.
    """
    where = os.path.dirname(module.__file__)
    filename = os.path.basename(module.__file__)
    filename = os.path.splitext(filename)[0] + ".py"

    with patch("sys.argv", new=argv):
        imp.load_source('__main__', os.path.join(where, filename))


def launch(cmd, **kwds):
    """Runs the command in a separate process and returns the lines of stdout and stderr
    as lists
    """
    if isinstance(cmd, string_types):
        cmd = [cmd]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, **kwds)
    out, err = p.communicate()

    # FIXME: can decoding below break on some unorthodox output?
    if out is not None and not isinstance(out, string_types):
        out = out.decode('utf-8')

    if err is not None and not isinstance(err, string_types):
        err = err.decode('utf-8')

    return (out, err)


class Shell(object):
    """Create a shell script which runs the command and optionally runs
    another program which returns to stdout/err retults to confirm success or failure
    """
    fname = None

    def __init__(self, func_commands, print_info=True, **kwds):
        if isinstance(func_commands, string_types):
            self.func_commands = [func_commands]
        else:
            self.func_commands = func_commands
        self.print_info = print_info
        self.kwds = kwds

    def __enter__(self):
        with closing(tempfile.NamedTemporaryFile('w', delete=False)) as f:
            self.cmd = f.name
            os.chmod(self.cmd, 0o777)
            f.write('#!/bin/sh\n')

            for line in self.func_commands:
                f.write('%s\n' % line)

        self.out, self.err = launch(self.cmd, **self.kwds)

        return self

    def __exit__(self, ee, ei, tb):  # @UnusedVariable
        if os.path.isfile(self.cmd):
            os.remove(self.cmd)

    def print_io(self):
        def print_out_err(name, data):
            print(name)
            if data.strip() == '':
                print(' <no data>')
            else:
                print()
                for line in data.split('\n')[:-1]:
                    print(line)

        print('+++ Shell +++')
        print('--cmd:')
        for line in self.func_commands:
            print('* %s' % line)
        print_out_err('--out', self.out)
        print_out_err('--err', self.err)
        print('=== Shell ===')


def _evaluate_fn_source(src, *args, **kwargs):
    locals_ = {}
    eval(compile(src, '<string>', 'single'), {}, locals_)
    fn = next(iter(locals_.values()))
    if isinstance(fn, staticmethod):
        fn = fn.__get__(None, object)
    return fn(*args, **kwargs)


def _invoke_method(obj, name, *args, **kwargs):
    return getattr(obj, name)(*args, **kwargs)


def _find_class_from_staticmethod(fn):
    for _, cls in inspect.getmembers(sys.modules[fn.__module__], inspect.isclass):
        for name, member in inspect.getmembers(cls):
            if member is fn or (isinstance(member, staticmethod) and member.__get__(None, object) is fn):
                return cls, name
    return None, None


def _make_pickleable(fn):
    # return a pickleable function followed by a tuple of initial arguments
    # could use partial but this is more efficient
    try:
        cPickle.dumps(fn, protocol=0)
    except TypeError:
        pass
    else:
        return fn, ()
    if inspect.ismethod(fn):
        name, self_ = fn.__name__, fn.__self__
        if self_ is None:  # Python 2 unbound method
            self_ = fn.im_class
        return _invoke_method, (self_, name)
    elif inspect.isfunction(fn) and fn.__module__ in sys.modules:
        cls, name = _find_class_from_staticmethod(fn)
        if (cls, name) != (None, None):
            try:
                cPickle.dumps((cls, name), protocol=0)
            except cPickle.PicklingError:
                pass
            else:
                return _invoke_method, (cls, name)
    # Fall back to sending the source code
    return _evaluate_fn_source, (textwrap.dedent(inspect.getsource(fn)),)


def _run_in_subprocess_redirect_stdout(fd):
    import os  # @Reimport
    import sys  # @Reimport
    sys.stdout.close()
    os.dup2(fd, 1)
    os.close(fd)
    sys.stdout = os.fdopen(1, 'w', 1)


def _run_in_subprocess_remote_fn(channel):
    from pkglib_util.six.moves import cPickle  # @UnresolvedImport @Reimport # NOQA
    fn, args, kwargs = cPickle.loads(channel.receive(-1))
    channel.send(cPickle.dumps(fn(*args, **kwargs), protocol=0))


def run_in_subprocess(fn, python=sys.executable, cd=None, timeout=(-1)):
    """ Wrap a function to run in a subprocess.  The function must be
        pickleable or otherwise must be totally self-contained; it must not
        reference a closure or any globals.  It can also be the source of a
        function (def fn(...): ...).

        Raises execnet.RemoteError on exception.
    """
    pkl_fn, preargs = (_evaluate_fn_source, (fn,)) if isinstance(fn, str) else _make_pickleable(fn)
    spec = '//'.join(filter(None, ['popen', 'python=' + python, 'chdir=' + cd if cd else None]))

    def inner(*args, **kwargs):
        # execnet sends stdout to /dev/null :(
        fix_stdout = sys.version_info < (3, 0, 0)  # Python 3 passes close_fds=True to subprocess.Popen
        with ExitStack() as stack:
            with ExitStack() as stack2:
                if fix_stdout:
                    fd = os.dup(1)
                    stack2.callback(os.close, fd)
                gw = execnet.makegateway(spec)  # @UndefinedVariable
                stack.callback(gw.exit)
            if fix_stdout:
                with closing(gw.remote_exec(_run_in_subprocess_remote_fn)) as chan:
                    chan.send(cPickle.dumps((_run_in_subprocess_redirect_stdout, (fd,), {}), protocol=0))
                    chan.receive(-1)
            with closing(gw.remote_exec(_run_in_subprocess_remote_fn)) as chan:
                payload = (pkl_fn, tuple(i for t in (preargs, args) for i in t), kwargs)
                chan.send(cPickle.dumps(payload, protocol=0))
                return cPickle.loads(chan.receive(timeout))
    return inner if isinstance(fn, str) else update_wrapper(inner, fn)
