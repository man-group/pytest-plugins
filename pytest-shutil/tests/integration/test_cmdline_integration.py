import os

from pytest_shutil import cmdline


def test_chdir():
    here = os.getcwd()
    with cmdline.chdir('/bin'):
        assert os.getcwd() == '/bin'
    assert os.getcwd() == here