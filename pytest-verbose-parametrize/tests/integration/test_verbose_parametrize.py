from distutils.dir_util import copy_tree

from pkg_resources import resource_filename  # @UnresolvedImport
import pytest


@pytest.fixture
def setup(virtualenv):
    test_dir = resource_filename('pytest_verbose_parametrize',
                                 'tests/integration/parametrize_ids')
    virtualenv.install_package('pytest-cov')
    virtualenv.install_package('pytest-verbose-parametrize')
    copy_tree(test_dir, virtualenv.workspace)


# XXX This plugin has stopped working with recent versions of pytest :(
@pytest.mark.xfail
def test_parametrize_ids_generates_ids(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_parametrized.py'],
                                           pytestconfig, cd=virtualenv.workspace)
    expected = '''<Module 'tests/unit/test_parametrized.py'>
  <Function 'test_foo[sum-list]'>
  <Function 'test_foo[len-int]'>
'''
    assert expected in output


@pytest.mark.xfail
def test_parametrize_ids_leaves_nonparametrized(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_non_parametrized.py'],
                                           pytestconfig, cd=virtualenv.workspace)
    expected = '''<Module 'tests/unit/test_non_parametrized.py'>
  <Function 'test_bar'>
'''
    assert expected in output


@pytest.mark.xfail
def test_handles_apparent_duplicates(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_duplicates.py'],
                                           pytestconfig, cd=virtualenv.workspace)
    expected = '''<Module 'tests/unit/test_duplicates.py'>
  <Function 'test_foo[0-[1]]'>
  <Function 'test_foo[0-[1]#1]'>
  <Function 'test_foo[0-[1]#2]'>
'''
    assert expected in output


@pytest.mark.xfail
def test_truncates_long_ids(pytestconfig, virtualenv, setup):
    output = virtualenv.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_long_ids.py'],
                                           pytestconfig, cd=virtualenv.workspace)
    expected = '''<Module 'tests/unit/test_long_ids.py'>
  <Function 'test_foo[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9...-None]'>
'''
    assert expected in output
