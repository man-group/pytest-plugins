from distutils.dir_util import copy_tree
import shutil

from pkg_resources import resource_filename
import pytest

from pytest_virtualenv import VirtualEnv

@pytest.yield_fixture(scope='session')
def virtualenv():
    with VirtualEnv() as venv:
        test_dir = resource_filename('pytest_profiling',
                                 'tests/integration/profile')
        venv.install_package('pytest-cov')
        venv.install_package('pytest-profiling')
        copy_tree(test_dir, venv.workspace)
        shutil.rmtree(venv.workspace / 'tests' / 'unit' / '__pycache__', ignore_errors=True)
        yield venv


def test_profile_profiles_tests(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile',
                                           'tests/unit/test_example.py'],
                                          pytestconfig, cd=virtualenv.workspace)
    assert 'test_example.py:1(test_foo)' in output


def test_profile_generates_svg(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile-svg',
                                          'tests/unit/test_example.py'],
                                          pytestconfig, cd=virtualenv.workspace)
    assert any(['test_example:1:test_foo' in i for i in 
                (virtualenv.workspace / 'prof/combined.svg').lines()])

    assert 'test_example.py:1(test_foo)' in output
    assert 'SVG' in output


def test_profile_long_name(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile',
                                           'tests/unit/test_long_name.py'],
                                          pytestconfig, cd=virtualenv.workspace)
    assert (virtualenv.workspace / 'prof/fbf7dc37.prof').isfile()


def test_profile_chdir(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--profile',
                                           'tests/unit/test_chdir.py'],
                                          pytestconfig, cd=virtualenv.workspace)
