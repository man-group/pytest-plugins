import os

from pytest_shutil import cmdline


def test_chdir():
    here = os.getcwd()
    bindir = os.path.realpath('/bin')
    with cmdline.chdir(bindir):
        assert os.getcwd() == bindir
    assert os.getcwd() == here


def test_chdir_goes_away(workspace):
    os.chdir(workspace.workspace)
    workspace.teardown()
    bindir = os.path.realpath('/bin')
    with cmdline.chdir(bindir):
        assert os.getcwd() == bindir
    assert os.getcwd() == '/'