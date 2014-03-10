import sys
import subprocess

from subprocess import CalledProcessError, PIPE

from mock import patch
from pytest import raises

from pkglib_util import cmdline


def get_python_cmd(cmd="", exit_code=0):
    cmd = cmd.strip()
    if cmd and not cmd.endswith(';'):
        cmd += ";"
    cmd = 'import sys; %s sys.exit(%d);' % (cmd, exit_code)
    return [sys.executable, '-c', cmd]


def test_cmdline_run_raises_on_failure():
    cmd = get_python_cmd(exit_code=1)

    with raises(CalledProcessError):
        cmdline.run(cmd)


def test_cmdline_run_logs_stdout_on_failure():
    cmd = get_python_cmd('sys.stdout.write("stdout")', exit_code=1)

    with patch('pkglib_util.cmdline.get_log') as get_log:
        with raises(CalledProcessError):
            cmdline.run(cmd, capture_stdout=True)

    expected = 'Command failed: "%s"\nstdout' % " ".join(cmd)
    get_log.return_value.error.assert_called_with(expected)


def test_cmdline_run_logs_stderr_on_failure():
    cmd = get_python_cmd('sys.stderr.write("stderr")', exit_code=1)

    with patch('pkglib_util.cmdline.get_log') as get_log:
        with raises(CalledProcessError):
            cmdline.run(cmd, capture_stderr=True)

    expected = 'Command failed: "%s"\nstderr' % " ".join(cmd)
    assert get_log.return_value.error.call_count == 1
    assert get_log.return_value.error.call_args[0][0].startswith(expected)


def test_cmdline_run_logs_stdout_and_stderr_on_failure():
    cmd = ('sys.stdout.write("stdout");'
           'sys.stdout.flush();'
           'sys.stderr.write("stderr");')
    cmd = get_python_cmd(cmd, exit_code=1)

    with patch('pkglib_util.cmdline.get_log') as get_log:
        with raises(CalledProcessError):
            cmdline.run(cmd, capture_stdout=True, capture_stderr=True)

    expected = 'Command failed: "%s"\nstdoutstderr' % " ".join(cmd)
    assert get_log.return_value.error.call_count == 1
    assert get_log.return_value.error.call_args[0][0].startswith(expected)


def test_cmdline_run_passes_stdout_if_not_captured():
    cmd = get_python_cmd('sys.stdout.write("stdout")')
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    p = subprocess.Popen([sys.executable, '-c',
                          """from pkglib_util import cmdline
cmdline.run([%s], capture_stdout=False)""" % cmd], stdout=PIPE)
    out, _ = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'


def test_cmdline_run_passes_stderr_if_not_captured():
    cmd = get_python_cmd('sys.stderr.write("stderr")')
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    p = subprocess.Popen([sys.executable, '-c', """from pkglib_util import cmdline
cmdline.run([%s], capture_stderr=False)""" % cmd], stderr=PIPE)
    _, err = p.communicate()
    assert p.returncode == 0
    assert 'stderr' in err.decode('utf-8')


def test_cmdline_run_passes_stdout_and_stderr_if_not_captured():
    cmd = ('sys.stdout.write("stdout"); sys.stderr.write("stderr");')
    cmd = ", ".join(['\'%s\'' % s for s in get_python_cmd(cmd)])

    p = subprocess.Popen([sys.executable, '-c', """from pkglib_util import cmdline
cmdline.run([%s], capture_stdout=False, capture_stderr=False)
""" % cmd], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'
    assert 'stderr' in err.decode('utf-8')


def test_cmdline_run_passes_stdout_if_not_captured_on_failure():
    cmd = get_python_cmd('sys.stdout.write("stdout")', exit_code=1)
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    p = subprocess.Popen([sys.executable, '-c', """from pkglib_util import cmdline
from subprocess import CalledProcessError
try:
    cmdline.run([%s], capture_stdout=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stdout=PIPE)
    out, _ = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'


def test_cmdline_run_passes_stderr_if_not_captured_on_failure():
    cmd = get_python_cmd('sys.stderr.write("stderr")', exit_code=1)
    cmd = ", ".join(['\'%s\'' % s for s in cmd])

    p = subprocess.Popen([sys.executable, '-c', """from pkglib_util import cmdline
from subprocess import CalledProcessError
try:
    cmdline.run([%s], capture_stderr=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stderr=PIPE)
    _, err = p.communicate()
    assert p.returncode == 0
    assert 'stderr' in err.decode('utf-8')


def test_cmdline_run_passes_stdout_and_stderr_if_not_captured_on_failure():
    cmd = ('sys.stdout.write("stdout");'
           'sys.stdout.flush();'
           'sys.stderr.write("stderr");')
    cmd = ", ".join(['\'%s\'' % s for s in get_python_cmd(cmd, exit_code=1)])

    p = subprocess.Popen([sys.executable, '-c', """from pkglib_util import cmdline
from subprocess import CalledProcessError
try:
    cmdline.run([%s], capture_stdout=False, capture_stderr=False)
except CalledProcessError:
    pass
else:
    raise RuntimeError
""" % cmd], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    assert p.returncode == 0
    assert out.decode('utf-8') == 'stdout'
    assert 'stderr' in err.decode('utf-8')
