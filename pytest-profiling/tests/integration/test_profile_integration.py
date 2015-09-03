from distutils.dir_util import copy_tree

from pkg_resources import resource_filename
import pytest


@pytest.fixture
def setup(virtualenv):
    test_dir = resource_filename('pytest_profiling',
                                 'tests/integration/profile')
    virtualenv.install_package('pytest-cov')
    virtualenv.install_package('pytest-profiling')
    copy_tree(test_dir, virtualenv.workspace)


def test_profile_profiles_tests(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile',
                                           'tests/unit/test_example.py'],
                                          pytestconfig, cd=virtualenv.workspace)
    assert 'test_example.py:1(test_foo)' in output


def test_profile_generates_svg(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile-svg',
                                          'tests/unit/test_example.py'],
                                          pytestconfig, cd=virtualenv.workspace)
    assert any(['test_example:1:test_foo' in i for i in 
                (virtualenv.workspace / 'prof/combined.svg').lines()])

    assert 'test_example.py:1(test_foo)' in output
    assert 'SVG' in output
