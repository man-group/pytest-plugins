import os
from subprocess import PIPE, STDOUT

from mock import patch, sentinel

from pkglib_util import cmdline


def test_cmdline_run_passes_stdout_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = (None, '')
        cmdline.run(sentinel.cmd, capture_stdout=False, capture_stderr=True)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=None, stderr=STDOUT)


def test_cmdline_run_passes_stderr_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = ('', None)
        cmdline.run(sentinel.cmd, capture_stdout=True, capture_stderr=False)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=PIPE, stderr=None)


def test_cmdline_run_passes_stdout_and_stderr_if_not_captured():
    with patch('subprocess.Popen') as Popen:
        Popen.return_value.returncode = 0
        Popen.return_value.communicate.return_value = (None, None)
        cmdline.run(sentinel.cmd, capture_stdout=False, capture_stderr=False)
    Popen.assert_called_with(sentinel.cmd, stdin=None, stdout=None, stderr=None)


def test_chdir():
    here = os.getcwd()
    with cmdline.chdir('/bin'):
        assert os.getcwd() == '/bin'
    assert os.getcwd() == here


def test_set_home():
    home = os.environ['HOME']
    with cmdline.set_home('/tmp'):
        assert os.environ['HOME'] == '/tmp'
    assert os.environ['HOME'] == home
