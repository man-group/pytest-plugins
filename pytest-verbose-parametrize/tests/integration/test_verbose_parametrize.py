import sys
import os

from pkg_resources import resource_filename, get_distribution  # @UnresolvedImport
from pytest_shutil.run import run_with_coverage

TEST_DIR = resource_filename('pytest_verbose_parametrize', 'tests/integration/parametrize_ids')
PYTEST = os.path.join(os.path.dirname(sys.executable), 'pytest')
PYTEST_VERSION = get_distribution("pytest").parsed_version
MODULE_PREFIX = "" if PYTEST_VERSION.major >= 8 else "tests/integration/parametrize_ids/tests/unit/"


def test_parametrize_ids_generates_ids(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_parametrized.py'],
                                pytestconfig, cd=TEST_DIR)
    expected_lines = [f"<Module {MODULE_PREFIX}test_parametrized.py", "<Function test_foo[sum-list]>", "<Function test_foo[len-int]>"]
    for line in expected_lines:
        assert line in output


def test_parametrize_ids_leaves_nonparametrized(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_non_parametrized.py'],
                                pytestconfig, cd=TEST_DIR)
    expected_lines = [f"<Module {MODULE_PREFIX}test_non_parametrized.py>", "<Function test_bar>"]
    for line in expected_lines:
        assert line in output


def test_handles_apparent_duplicates(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_duplicates.py'],
                                pytestconfig, cd=TEST_DIR)
    expected = f'''<Module {MODULE_PREFIX}test_duplicates.py>
<Function test_foo[0-[1]]>
<Function test_foo[0-[1]#1]>
<Function test_foo[0-[1]#2]>
'''
    expected_lines = expected.splitlines()
    for line in expected_lines:
        assert line in output


def test_truncates_long_ids(pytestconfig):
    output = run_with_coverage([PYTEST, '--collectonly', 'tests/unit/test_long_ids.py'],
                               pytestconfig, cd=TEST_DIR)
    expected = f'''<Module {MODULE_PREFIX}test_long_ids.py>
<Function test_foo[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9...-None]>
'''
    expected_lines = expected.splitlines()
    for line in expected_lines:
        assert line in output
