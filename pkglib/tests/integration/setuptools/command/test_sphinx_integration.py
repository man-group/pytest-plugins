from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate
HERE = os.getcwd()


def test_sphinx(pytestconfig):
    """ Creates template, builds doco
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir,
                                     'build_sphinx'], pytestconfig, cd=HERE))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc',
                                           'acme.foo.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx',
                                           'html', 'index.html'))


def test_sphinx_multilevel_package(pytestconfig):
    """ Creates template, builds doco for multi-level namespace packages
    """
    with PkgTemplate(name='acme.foo.bar.baz') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir,
                                     'build_sphinx'], pytestconfig, cd=HERE))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc',
                                           'acme.foo.bar.baz.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx',
                                           'html', 'index.html'))


def test_sphinx_autodoc_dynamic(pytestconfig):
    """ Creates template, builds doco using dynamic autodoc.
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir,
                                     'build_sphinx', '--autodoc-dynamic'],
                                    pytestconfig, cd=HERE))

        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc',
                                           'acme.foo.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx',
                                           'html', 'index.html'))
