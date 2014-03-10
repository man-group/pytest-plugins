from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate

HERE = os.getcwd()


def test_develop(pytestconfig):
    """ Creates template, runs setup.py develop then does some checks that the
    package was setup properly.
    """
    with PkgTemplate('acme.foo-1.0.dev1', install_requires='flake8') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE))
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
            '%s %s/bin/foo -h' % (pkg.python, pkg.virtualenv),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo'].issrc
        assert installed['flake8'].isdev


def test_develop_non_acme_namespace(pytestconfig):
    """ As above, using a non-acme namespace
    """
    with PkgTemplate('fx.foobar-1.0.dev1', install_requires='flake8') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir,
                                     'develop', '-q'],
                                    pytestconfig, cd=HERE))
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import fx.foobar"' % pkg.python,
            '%s %s/bin/foobar -h' % (pkg.python, pkg.virtualenv),
        ]]
        installed = pkg.installed_packages()
        assert installed['fx.foobar'].issrc
        assert installed['flake8'].isdev


def test_develop_hyphenated(pytestconfig):
    """ As above, using a hyphenated package name
    """
    with PkgTemplate('acme.foo-bar-1.0.dev1',
                     install_requires='flake8') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir,
                                     'develop', '-q'], pytestconfig, cd=HERE))
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo_bar"' % pkg.python,
            '%s %s/bin/foo_bar -h' % (pkg.python, pkg.virtualenv),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo-bar'].issrc
        assert installed['flake8'].isdev


def test_develop_final(pytestconfig):
    """ Creates template, runs setup.py develop with the prefer final option
        was setup properly.
    """
    with PkgTemplate(name='acme.foo-1.0.dev1', install_requires='nose') as pkg:
        pkg.install_package('pytest-cov')
        cmd = ['%s/setup.py' % pkg.trunk_dir, 'develop', '-q', '--prefer-final']
        print(pkg.run_with_coverage(cmd, pytestconfig, cd=HERE))
        for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
            '%s %s/bin/foo -h' % (pkg.python, pkg.virtualenv),
            ('%s %s/setup.py depgraph -et --boxart' %
             (pkg.python, pkg.trunk_dir)),
        ]:
            pkg.run(cmd, capture=False, cd=HERE)
        installed = pkg.installed_packages()
        assert installed['acme.foo'].issrc
        assert installed['nose'].isrel
