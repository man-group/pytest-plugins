import os

from pkglib import pyenv


def test_create_virtualenv_temp():
    with pyenv.VirtualEnv() as v:

        assert os.path.isfile(v.executable)
        assert os.access(v.executable, os.X_OK)

        assert os.path.isfile(v.real_executable)
        assert os.access(v.real_executable, os.X_OK)


def _check_permissions(root):
    for path, dirnames, filenames in os.walk(root):
        for dirname in dirnames:
            assert os.stat(os.path.join(path, dirname)).st_mode & 0o555 == 0o555
        for filename in filenames:
            # easy_install.unpack_and_compile,
            # ahl.pkgutils.setuptools.buildout.fix_permissions
            exe = os.path.splitext(filename)[1] in ('py', 'dll', 'so')
            expected = 0o555 if (exe and 'EGG_INFO' not in path) else 0o444
            mode = os.stat(os.path.join(path, filename)).st_mode
            assert mode & expected == expected


def test_virtualenv_permissions():
    with pyenv.VirtualEnv() as v:
        _check_permissions(v.dir)


def test_virtualenv_permissions_with_pkgutils():
    with pyenv.VirtualEnv(delete=False) as v:
        v.install_package('distribute>=0.6.36', debug=True, verbose=True)
        v.install_package('pytest')
        _check_permissions(v.dir)