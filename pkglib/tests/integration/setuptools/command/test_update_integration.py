from __future__ import print_function
import os

from pkglib_testing.util import PkgTemplate
HERE = os.getcwd()


def test_update(pytestconfig):
    """ Creates template, runs setup.py update
    """
    # TODO: check behaviour
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop',
                                     '-q'], pytestconfig, cd=HERE))
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'update'],
                                    pytestconfig, cd=HERE))
