from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate, TmpVirtualEnv
HERE = os.getcwd()


def test_uninstall_setuptools(pytestconfig):  # @UnusedVariable
    """ Creates template, runs easy_install then uninstall
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')

        pkg.install_package('pytz', installer='easy_install')
        assert 'pytz' in pkg.installed_packages()
        pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'uninstall',
                               '--yes', 'pytz'], pytestconfig, cd=HERE)
        assert 'pytz' not in pkg.installed_packages()


def test_uninstall_command(pytestconfig):  # @UnusedVariable
    with TmpVirtualEnv() as venv:
        venv.install_package('pkglib', installer='easy_install')
        venv.install_package('pytest-cov')

        venv.install_package('pytz', installer='easy_install')
        assert 'pytz' in venv.installed_packages()
        venv.run_with_coverage(['%s/bin/pyuninstall' % venv.virtualenv,
                                '--yes', 'pytz'], pytestconfig, cd=HERE)
        assert 'pytz' not in venv.installed_packages()
