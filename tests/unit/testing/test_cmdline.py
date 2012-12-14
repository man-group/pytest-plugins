from pkglib.testing import cmdline
from pkglib.testing.util import patch_getpass, patch_raw_input

def test_run_as_main():
    def foo():
        import sys
        assert sys.argv[1] == 'bar'
        assert sys.argv[2] == 'baz'
    cmdline.run_as_main(foo, 'bar', 'baz')

def test_patch_getpass():
    username = 'admin'
    password = 'password'
    with patch_getpass(username, password):
        import getpass
        assert getpass.getuser() == username
        assert getpass.getpass() == password

def test_patch_raw_input():
    user_input = 'foo'
    with patch_raw_input(user_input):
        assert raw_input() == user_input
