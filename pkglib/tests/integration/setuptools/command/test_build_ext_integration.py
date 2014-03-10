from __future__ import print_function
import os
from distutils.dir_util import copy_tree

from pkglib_testing.util import PkgTemplate

HERE = os.getcwd()


def test_cython_build_ext(pytestconfig):
    """ Creates template, runs setup.py develop which will invoke build_ext
    which for this project template contains cython template files
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'cython')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE))
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
        ]]
        exec_code = ("from acme.foo import _mycython; "
                     "print(_mycython.test_cython([1,2,3]))")

        output = pkg.run('%s -c "%s"' % (pkg.python, exec_code), capture=True)

        assert output.strip() == "[2, 4, 6]"


def test_cython_build_ext_cpp(pytestconfig):
    """ Creates template, runs setup.py develop which will invoke build_ext
    which for this project template contains cython template files for C++
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'cython_cpp')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        print(pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE))
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
        ]]
        exec_code = ("from acme.foo import _cppcython; "
                     "print(_cppcython.test_cpp_cython([1,2,3,4]))")

        output = pkg.run('%s -c "%s"' % (pkg.python, exec_code), capture=True)

        assert output.strip() == "[0.5, 1.0, 1.5, 2.0]"
