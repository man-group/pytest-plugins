import os

from pkglib_testing.util import PkgTemplate

HERE = os.getcwd()
STATIC_DATA = 'STATIC DATA\n'


def test_easy_install_install_static_data_symlink(pytestconfig):
    with PkgTemplate('acme.foo-1.0.dev1',
                     entry_points={'acme.static_data': 'foo = acme.foo:static'}
                     ) as pkg:
        pkg.delete = False
        open(os.path.join(pkg.trunk_dir, 'acme', 'foo', 'static'),
             'w').write(STATIC_DATA)
        open(os.path.join(pkg.trunk_dir, 'MANIFEST.in'),
             'w').write("include acme/foo/static\n")
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'install'],
                                    pytestconfig, cd=HERE))
        assert os.path.islink(os.path.join(pkg.virtualenv, 'share', 'foo'))
        assert open(os.path.join(pkg.virtualenv, 'share', 'foo'),
                    'r').read() == STATIC_DATA


def test_easy_install_develop_static_data_symlink(pytestconfig):
    with PkgTemplate('acme.foo-1.0.dev1',
                     entry_points={'acme.static_data': 'foo = acme.foo:static'}
                     ) as pkg:
        pkg.delete = False
        open(os.path.join(pkg.trunk_dir, 'acme', 'foo', 'static'),
             'w').write(STATIC_DATA)
        open(os.path.join(pkg.trunk_dir, 'MANIFEST.in'),
             'w').write("include acme/foo/static\n")
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE))
        assert os.path.islink(os.path.join(pkg.virtualenv, 'share', 'foo'))
        assert (os.readlink(os.path.join(pkg.virtualenv, 'share', 'foo')) ==
                os.path.join(pkg.trunk_dir, 'acme', 'foo', 'static'))
        assert open(os.path.join(pkg.virtualenv, 'share', 'foo'),
                    'r').read() == STATIC_DATA
