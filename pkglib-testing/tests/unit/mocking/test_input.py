from pkglib_testing.mocking.input import patch_getpass, patch_raw_input


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
