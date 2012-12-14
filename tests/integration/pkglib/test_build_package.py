"""
Tests covering all the setuptools extensions, except for
upload, register and upload_docs which are done in test_pypi_integration
"""
import path

from pkglib.testing.util import PkgTemplate


HERE = path.path.getcwd()


def test_core_package(pytestconfig):
    """ Creates template, runs setup.py develop then does some checks that the package
        was setup properly.
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='acme.foo', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
            '%s/bin/foo -h' % pkg.virtualenv,
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo'].issrc
        assert installed['acme.bar'].isdev


def test_non_inhouse_namespace(pytestconfig):
    """ As above, using a non-inhouse namespace
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='mesa.foobar', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import mesa.foobar"' % pkg.python,
            '%s/bin/foobar -h' % pkg.virtualenv,
        ]]
        installed = pkg.installed_packages()
        assert installed['mesa.foobar'].issrc
        assert installed['acme.bar'].isdev


def test_multi_level_namespace(pytestconfig):
    """ As above, using a multi-level namespace
    """
    with PkgTemplate(name='acme.foo.bar') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo.bar"' % pkg.python,
            '%s/bin/acme.foo.bar -h' % pkg.virtualenv,
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo.bar'].issrc
        assert (path.path(pkg.trunk_dir) / 'acme' / 'foo' / 'bar' / '__init__.py').isfile()
