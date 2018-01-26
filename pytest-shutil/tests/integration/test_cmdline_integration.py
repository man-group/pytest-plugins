import os

from pytest_shutil import cmdline


def test_chdir():
    here = os.getcwd()
    with cmdline.chdir('/bin'):
        assert os.getcwd() == '/bin'
    assert os.getcwd() == here

def test_chdir_goes_away(workspace):
    os.chdir(workspace.workspace)
    workspace.teardown()
    with cmdline.chdir('/bin'):
        assert os.getcwd() == '/bin'
    assert os.getcwd() == '/'