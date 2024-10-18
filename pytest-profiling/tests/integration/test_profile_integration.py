import shutil
from distutils.dir_util import copy_tree
from pathlib import Path

import pytest

try:
    from importlib.metadata import distribution
except ImportError:
    from importlib_metadata import distribution

try:
    from importlib.resources import as_file, files
except ImportError:
    from importlib_resources import as_file, files

    def resource_filename(package, resource):
        return files(package) / resource


from pytest_virtualenv import VirtualEnv


@pytest.yield_fixture(scope="session")
def virtualenv():
    with VirtualEnv() as venv:
        test_dir = Path(__file__).parent / "profile"

        venv.install_package("more-itertools")

        # Keep pytest version the same as what's running this test to ensure P27 keeps working
        venv.install_package("pytest=={}".format(distribution("pytest").version))

        venv.install_package("pytest-cov")
        venv.install_package("pytest-profiling")
        copy_tree(str(test_dir), str(venv.workspace))
        shutil.rmtree(
            venv.workspace / "tests" / "unit" / "__pycache__", ignore_errors=True
        )
        yield venv


def test_profile_profiles_tests(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(
        ["-m", "pytest", "--profile", "tests/unit/test_example.py"],
        pytestconfig,
        cd=virtualenv.workspace,
    )
    assert "test_example.py:1(test_foo)" in output


def test_profile_generates_svg(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(
        ["-m", "pytest", "--profile-svg", "tests/unit/test_example.py"],
        pytestconfig,
        cd=virtualenv.workspace,
    )
    assert any(
        [
            "test_example:1:test_foo" in i
            for i in (virtualenv.workspace / "prof/combined.svg").open().readlines()
        ]
    )

    assert "test_example.py:1(test_foo)" in output
    assert "SVG" in output


def test_profile_long_name(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(
        ["-m", "pytest", "--profile", "tests/unit/test_long_name.py"],
        pytestconfig,
        cd=virtualenv.workspace,
    )
    assert (virtualenv.workspace / "prof/fbf7dc37.prof").is_file()


def test_profile_chdir(pytestconfig, virtualenv):
    output = virtualenv.run_with_coverage(
        ["-m", "pytest", "--profile", "tests/unit/test_chdir.py"],
        pytestconfig,
        cd=virtualenv.workspace,
    )
