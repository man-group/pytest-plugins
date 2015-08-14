import subprocess
import sys
import os
import time
import pytest
import execnet
import inspect
import textwrap
from uuid import uuid4

from pkglib_testing import cmdline
from pkglib_testing.fixtures import workspace


def test_workspace_run_displays_output_on_failure():
    p = subprocess.Popen([sys.executable, '-c', """from pkglib_testing.fixtures.workspace import Workspace
from subprocess import CalledProcessError
try:
    Workspace().run('echo stdout; echo stderr >&2; false', capture=True)
except CalledProcessError:
    pass
else:
    raise RuntimeError("did not raise")
"""], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0]
    assert p.returncode == 0
    assert 'stdout\n'.encode('utf-8') in out
    assert 'stderr\n'.encode('utf-8') in out


def test_run_in_subprocess():
    def fn():
        return None
    res = cmdline.run_in_subprocess(fn)()
    assert res is None


def test_run_in_subprocess_is_a_subprocess():
    pid = cmdline.run_in_subprocess(os.getpid)()
    assert pid != os.getpid()


def test_run_in_subprocess_uses_passed_python():
    def fn():
        import sys  # @Reimport
        return sys.executable
    python = cmdline.run_in_subprocess(fn, python=sys.executable)()
    assert python == sys.executable


def test_run_in_subprocess_cd():
    with workspace.Workspace() as ws:
        cwd = cmdline.run_in_subprocess(os.getcwd, cd=ws.workspace)()
    assert cwd == ws.workspace


def test_run_in_subprocess_timeout():
    with pytest.raises(execnet.TimeoutError) as exc:  # @UndefinedVariable
        cmdline.run_in_subprocess(time.sleep, timeout=0)(1)
    assert 'no item after 0 seconds' in str(exc.value)


def test_run_in_subprocess_exception():
    def fn(v):
        raise v
    v = ValueError(uuid4())
    with pytest.raises(execnet.RemoteError) as exc:  # @UndefinedVariable
        cmdline.run_in_subprocess(fn)(v)
    assert str(v) in str(exc.value)


@pytest.mark.xfail('sys.version_info >= (3, 0, 0)')
def test_run_in_subprocess_passes_stdout():
    def fn(x):
        import sys  # @Reimport
        sys.stdout.write(x)
    guid = str(uuid4())
    cmd = """from pkglib_testing.cmdline import run_in_subprocess
run_in_subprocess(%r)(%r)
""" % (textwrap.dedent(inspect.getsource(fn)), guid)
    p = subprocess.Popen([sys.executable, '-c', cmd], stdout=subprocess.PIPE)
    (out, _) = p.communicate()
    assert out == guid


def test_run_in_subprocess_passes_stderr():
    def fn(x):
        import sys  # @Reimport
        sys.stderr.write(x)
    guid = str(uuid4())
    cmd = """from pkglib_testing.cmdline import run_in_subprocess
run_in_subprocess(%r)(%r)
""" % (textwrap.dedent(inspect.getsource(fn)), guid)
    p = subprocess.Popen([sys.executable, '-c', cmd], stderr=subprocess.PIPE)
    (_, err) = p.communicate()
    assert guid in err.decode('ascii')
