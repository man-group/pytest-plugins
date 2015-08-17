import subprocess
import sys
import os
import time
import pytest
import execnet
import inspect
import textwrap
from uuid import uuid4

import mock

from pytest_shutil import run, workspace
from pytest_shutil.env import no_cov


def get_python_cmd(cmd="", exit_code=0):
    cmd = cmd.strip()
    if cmd and not cmd.endswith(';'):
        cmd += ";"
    cmd = 'import sys; %s sys.exit(%d);' % (cmd, exit_code)
    return [sys.executable, '-c', cmd]


def test_run_raises_on_failure():
    cmd = get_python_cmd(exit_code=1)
    with pytest.raises(subprocess.CalledProcessError):
        with no_cov():
            run.run(cmd)


def test_run_logs_stdout_on_failure():
    cmd = get_python_cmd('sys.stdout.write("stdout")', exit_code=1)

    with mock.patch('pytest_shutil.run.log') as log:
        with pytest.raises(subprocess.CalledProcessError):
            with no_cov():
                run.run(cmd, capture_stdout=True)

    expected = 'Command failed: "%s"\nstdout' % " ".join(cmd)
    log.error.assert_called_with(expected)


def test_run_logs_stderr_on_failure():
    cmd = get_python_cmd('sys.stderr.write("stderr")', exit_code=1)

    with mock.patch('pytest_shutil.run.log') as log:
        with pytest.raises(subprocess.CalledProcessError):
            with no_cov():
                run.run(cmd, capture_stderr=True)

    expected = 'Command failed: "%s"\nstderr' % " ".join(cmd)
    assert log.error.call_count == 1
    assert log.error.call_args[0][0].startswith(expected)


def test_run_logs_stdout_and_stderr_on_failure():
    cmd = ('sys.stdout.write("stdout");'
           'sys.stdout.flush();'
           'sys.stderr.write("stderr");')
    cmd = get_python_cmd(cmd, exit_code=1)

    with mock.patch('pytest_shutil.run.log') as log:
        with pytest.raises(subprocess.CalledProcessError):
            with no_cov():
                run.run(cmd, capture_stdout=True, capture_stderr=True)

    expected = 'Command failed: "%s"\nstdoutstderr' % " ".join(cmd)
    assert log.error.call_count == 1
    assert log.error.call_args[0][0].startswith(expected)


def test_run_passes_stdout_if_not_captured():
    cmd = get_python_cmd('sys.stdout.write("stdout")')
    cmd = ", ".join(['\'%s\'' % s for s in cmd])
    with no_cov():
        p = subprocess.Popen([sys.executable, '-c',
                              """from pytest_shutil import run
run.run([%s], capture_stdout=False)""" % cmd], stdout=subprocess.PIPE)
    out, _ = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'


def test_run_passes_stderr_if_not_captured():
    cmd = get_python_cmd('sys.stderr.write("stderr")')
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', """from pytest_shutil import run
run.run([%s], capture_stderr=False)""" % cmd], stderr=subprocess.PIPE)
    _, err = p.communicate()
    assert p.returncode == 0
    assert 'stderr' in err.decode('utf-8')


def test_run_passes_stdout_and_stderr_if_not_captured():
    cmd = ('sys.stdout.write("stdout"); sys.stderr.write("stderr");')
    cmd = ", ".join(['\'%s\'' % s for s in get_python_cmd(cmd)])

    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', """from pytest_shutil import run
run.run([%s], capture_stdout=False, capture_stderr=False)
""" % cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'
    assert 'stderr' in err.decode('utf-8')


def test_run_passes_stdout_if_not_captured_on_failure():
    cmd = get_python_cmd('sys.stdout.write("stdout")', exit_code=1)
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', """from pytest_shutil import run
from subprocess import CalledProcessError
try:
    run.run([%s], capture_stdout=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stdout=subprocess.PIPE)
    out, _ = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'


def test_run_passes_stderr_if_not_captured_on_failure():
    cmd = get_python_cmd('sys.stderr.write("stderr")', exit_code=1)
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', """from pytest_shutil import run
from subprocess import CalledProcessError
try:
    run.run([%s], capture_stderr=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stderr=subprocess.PIPE)
    _, err = p.communicate()
    assert p.returncode == 0
    assert 'stderr' in err.decode('utf-8')


def test_run_passes_stdout_and_stderr_if_not_captured_on_failure():
    cmd = ('sys.stdout.write("stdout");'
           'sys.stdout.flush();'
           'sys.stderr.write("stderr");')
    cmd = ", ".join(['\'%s\'' % s for s in get_python_cmd(cmd, exit_code=1)])

    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', """from pytest_shutil import run
from subprocess import CalledProcessError
try:
    run.run([%s], capture_stdout=False, capture_stderr=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'
    assert 'stderr' in err.decode('utf-8')

def test_run_in_subprocess():
    def fn():
        return None
    with no_cov():
        res = run.run_in_subprocess(fn)()
    assert res is None


def test_run_in_subprocess_is_a_subprocess():
    pid = run.run_in_subprocess(os.getpid)()
    assert pid != os.getpid()


def test_run_in_subprocess_uses_passed_python():
    def fn():
        import sys  # @Reimport
        return sys.executable
    with no_cov():
        python = run.run_in_subprocess(fn, python=sys.executable)()
    assert python == sys.executable


def test_run_in_subprocess_cd():
    with workspace.Workspace() as ws:
        with no_cov():
            cwd = run.run_in_subprocess(os.getcwd, cd=ws.workspace)()
    assert cwd == ws.workspace


def test_run_in_subprocess_timeout():
    with pytest.raises(execnet.TimeoutError) as exc:  # @UndefinedVariable
        with no_cov():
            run.run_in_subprocess(time.sleep, timeout=0)(1)
    assert 'no item after 0 seconds' in str(exc.value)


def test_run_in_subprocess_exception():
    def fn(v):
        raise v
    v = ValueError(uuid4())
    with pytest.raises(execnet.RemoteError) as exc:  # @UndefinedVariable
        with no_cov():
            run.run_in_subprocess(fn)(v)
    assert str(v) in str(exc.value)


@pytest.mark.xfail('sys.version_info >= (3, 0, 0)')
def test_run_in_subprocess_passes_stdout():
    def fn(x):
        import sys  # @Reimport
        sys.stdout.write(x)
    guid = str(uuid4())
    cmd = """from pytest_shutil.run import run_in_subprocess
run_in_subprocess(%r)(%r)
""" % (textwrap.dedent(inspect.getsource(fn)), guid)
    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', cmd], stdout=subprocess.PIPE)
    (out, _) = p.communicate()
    assert out == guid


def test_run_in_subprocess_passes_stderr():
    def fn(x):
        import sys  # @Reimport
        sys.stderr.write(x)
    guid = str(uuid4())
    cmd = """from pytest_shutil.run import run_in_subprocess
run_in_subprocess(%r)(%r)
""" % (textwrap.dedent(inspect.getsource(fn)), guid)
    with no_cov():
        p = subprocess.Popen([sys.executable, '-c', cmd], stderr=subprocess.PIPE)
    (_, err) = p.communicate()
    assert guid in err.decode('ascii')
