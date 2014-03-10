from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate
HERE = os.getcwd()


def test_test():
    """ Creates template, runs setup.py test (without first running setup.py
    develop)
    """
    with PkgTemplate(name='acme.foo') as pkg:
        # This one won't run under coverage
        [pkg.run(cmd, capture=False) for cmd in [
            '%s %s/setup.py test' % (pkg.python, pkg.trunk_dir),
        ]]


def test_develop_then_test(pytestconfig):
    """ Creates template, runs setup.py develop then test
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'test'],
                                    pytestconfig, cd=HERE))


def test_test_hudson_mode(pytestconfig):
    """ Creates template, runs setup.py test in hudson mode
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'test',
                                     '-H'], pytestconfig, cd=HERE))
