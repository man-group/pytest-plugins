import stat
import os

from pytest_shutil import cmdline


def test_umask(workspace):
    f = workspace.workspace / 'foo'
    with cmdline.umask(0o202):
        f.touch()
    assert (f.stat().st_mode & 0o777) == 0o464

def test_pretty_formatter():
    f = cmdline.PrettyFormatter()
    f.title('A Title')
    f.hr()
    f.p('A Paragraph', 'red')
    assert f.buffer == [
        '\x1b[1m\x1b[34m  A Title\x1b[0m', 
        '\x1b[1m\x1b[34m--------------------------------------------------------------------------------\x1b[0m',
        '\x1b[31mA Paragraph\x1b[0m'
        ]
    f.flush()


def test_tempdir():
    with cmdline.TempDir() as d:
        assert os.path.exists(d)
    assert not os.path.exists(d)


def test_copy_files(workspace):
    d1 = workspace.workspace / 'd1'
    d2 = workspace.workspace / 'd2'
    d1.makedirs()
    d2.makedirs()
    (d1 / 'foo').touch()
    (d1 / 'bar').touch()
    cmdline.copy_files(d1, d2)
    assert (d2 / 'foo').exists()
    assert (d2 / 'bar').exists()
