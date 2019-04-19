import sys
import os
from distutils.dir_util import copy_tree

from pkg_resources import resource_filename  # @UnresolvedImport
from pytest_shutil.run import run_with_coverage

TEST_DIR = resource_filename('pytest_verbose_parametrize', 'tests/integration/parametrize_ids')
PYTEST = os.path.join(os.path.dirname(sys.executable), 'py.test')


def _update_expected(expected, output):
    """If pytest >= 4.1.0 is used, remove single quotes from expected output.

    This function allows to successfully assert output using version of pytest
    with or without pytest-dev/pytest@e9b2475e2 (Display actual test ids in `--collect-only`)
    introduced in version 4.1.0.
    """
    pytest_410_and_above = ".py'>" not in output
    return expected.replace("'", "") if pytest_410_and_above else expected


def test_parametrize_ids_generates_ids(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_parametrized.py'],
                                pytestconfig, cd=TEST_DIR)
    expected = '''<Module 'tests/integration/parametrize_ids/tests/unit/test_parametrized.py'>
  <Function 'test_foo[sum-list]'>
  <Function 'test_foo[len-int]'>
'''
    expected = _update_expected(expected, output)
    assert expected in output


def test_parametrize_ids_leaves_nonparametrized(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_non_parametrized.py'],
                                pytestconfig, cd=TEST_DIR)
    expected = '''<Module 'tests/integration/parametrize_ids/tests/unit/test_non_parametrized.py'>
  <Function 'test_bar'>
'''
    expected = _update_expected(expected, output)
    assert expected in output


def test_handles_apparent_duplicates(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_duplicates.py'],
                                pytestconfig, cd=TEST_DIR)
    expected = '''<Module 'tests/integration/parametrize_ids/tests/unit/test_duplicates.py'>
  <Function 'test_foo[0-[1]]'>
  <Function 'test_foo[0-[1]#1]'>
  <Function 'test_foo[0-[1]#2]'>
'''
    expected = _update_expected(expected, output)
    assert expected in output


def test_truncates_long_ids(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_long_ids.py'],
                               pytestconfig, cd=TEST_DIR)
    expected = '''<Module 'tests/integration/parametrize_ids/tests/unit/test_long_ids.py'>
  <Function 'test_foo[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9...-None]'>
'''
    expected = _update_expected(expected, output)
    assert expected in output
