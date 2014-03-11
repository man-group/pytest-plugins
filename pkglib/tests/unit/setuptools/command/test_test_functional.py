import os
import sys

from collections import defaultdict

import pytest

from mock import Mock, sentinel

from pkglib.config import org
from pkglib.setuptools.command import test

from .runner import (SavedBytesIO, _add_mock, _add_module_mock, _get_mock_dict,
                     _make_root_dir_from, _open_func_path, run_setuptools_cmd)


def clear_hudson_env(mocks):
    environ = _get_mock_dict(mocks, "os.environ")
    if "BUILD_TAG" in environ:
        del environ["BUILD_TAG"]
    if "WORKSPACE" in environ:
        del environ["WORKSPACE"]


def _enable_hudson_via_cmd_arg(mocks):
    clear_hudson_env(mocks)
    mocks["sys.argv"] = sys.argv[:1] + ["--hudson"]


def _enable_hudson_via_environment(mocks):
    environ = _get_mock_dict(mocks, "os.environ")
    if "WORKSPACE" in environ:
        del environ["WORKSPACE"]
    environ['BUILD_TAG'] = 'jenkins12345'
    mocks["sys.argv"] = sys.argv[:1] + ["--hudson"]


def _enable_hudson_via_cmd_arg_with_ws(mocks, workspace):
    _enable_hudson_via_cmd_arg(mocks)
    _get_mock_dict(mocks, "os.environ")['WORKSPACE'] = workspace


def _enable_hudson_via_environment_with_ws(mocks, workspace):
    _enable_hudson_via_environment(mocks)
    _get_mock_dict(mocks, "os.environ")['WORKSPACE'] = workspace


def _prepare_test_cmd_mocks(cwd=_make_root_dir_from("<test_pylint_cwd>"),
                            pylint_output="",
                            mocks=None):
    if mocks is None:
        mocks = {}

    mocks['pkglib.setuptools.command.test.CONFIG'] = org.OrganisationConfig(
                    test_linter=sentinel.linter,
                    test_linter_package=sentinel.linter_pkg,)

    mocks["os.getcwd"] = Mock(return_value=cwd)
    mocks["os.path.isdir"] = Mock(return_value=True)
    mocks["pkglib.setuptools.command.test.test.get_test_roots"] = Mock(return_value=['tests'])

    # Mock output from checkstyle
    communicate_mock = Mock(return_value=(pylint_output, ""))
    mock_subprocess = Mock(return_value=Mock(returncode=0,
                                             communicate=communicate_mock))
    mocks["subprocess.Popen"] = mock_subprocess

    # Mock os.open() so that PyLint produce by test command is captured and
    # can be examined
    _unpatched_open = open
    output_files = defaultdict(SavedBytesIO)

    mock_open = Mock()
    mock_open.__output_files = output_files

    def pylint_open_mock_func(*a, **kw):
        return (output_files[a[0]] if a[0].endswith(test.HUDSON_XML_PYLINT)
                else _unpatched_open(*a, **kw))

    mock_open.side_effect = pylint_open_mock_func
    mocks[_open_func_path] = mock_open

    # Mock remaining supporting infrastructure
    _add_mock(mocks, "pytest.main", lambda: Mock(return_value=0))
    _add_mock(mocks, "pkglib.setuptools.buildout.install")

    return mocks


def run_test_cmd_expect_system_exit(mocks, expected_rcode=0, args=None,
                                    dist_attrs=None):
    with pytest.raises(SystemExit) as ex:
        run_setuptools_cmd(test.test, args=args, mocks=mocks,
                           dist_attrs=dist_attrs)

    assert ex.value.code == expected_rcode


def assert_requirements_installed(mocks, reqs,
                                  kw_args={'prefer_final': False,
                                           'add_to_global': True,
                                           'use_existing': True}):
    buildout_install_mock = mocks["pkglib.setuptools.buildout.install"]
    assert buildout_install_mock.call_count == 1
    assert sorted(buildout_install_mock.call_args[0][1]) == sorted(reqs)
    assert buildout_install_mock.call_args[1] == kw_args


def assert_pytest_was_invoked(mocks, cwd=None):
    if cwd is None:
        cwd = mocks["os.getcwd"]()
    assert mocks["pytest.main"].call_once_with(args=['--verbose',
                                                     '--cov-report=term',
                                                     cwd])


def assert_pytest_and_pylint_were_invoked(mocks):
    assert_pytest_was_invoked(mocks)
    popen_mock = mocks["subprocess.Popen"]
    assert popen_mock.call_count == 1
    assert popen_mock.call_args[0] == ([sentinel.linter],)

    assert_requirements_installed(mocks, ["pytest", "pytest-cov", sentinel.linter_pkg])


def assert_pylint_was_written(mocks, pylint_output_file, expected_output):
    output_files = mocks[_open_func_path].__output_files

    assert len(output_files) == 1
    assert pylint_output_file in output_files

    actual_output = output_files[pylint_output_file].string_value
    assert actual_output == expected_output


def assert_no_pylint_was_written(mocks):
    for pylint_output in mocks[_open_func_path].__output_files.values():
        assert not pylint_output.string_value


def _test_hudson__pylint_is_written_to_non_base_dir(enable_hudson_mode,
                                                    non_base_dir,
                                                    dist_attrs={}):
    cwd = _make_root_dir_from("<some_base_dir>")
    original_cwd = _make_root_dir_from(non_base_dir)
    pylint_output = "Testing paths are amended"

    relpath = os.path.relpath(cwd, original_cwd) + os.path.sep
    expected_pylint_file_location = os.path.join(original_cwd,
                                                 test.HUDSON_XML_PYLINT)
    expected_output = relpath + pylint_output + '\n'

    mocks = _prepare_test_cmd_mocks(cwd=cwd, pylint_output=pylint_output)
    enable_hudson_mode(mocks)

    run_test_cmd_expect_system_exit(mocks, dist_attrs=dist_attrs)

    assert_pytest_and_pylint_were_invoked(mocks)
    assert_pylint_was_written(mocks, expected_pylint_file_location,
                              expected_output)


def test_run__invoked_without_hudson_nor_args__invokes_pytest_only():
    cwd = _make_root_dir_from("<somewhere>")
    expected_installed_reqs = ["pytest", "pytest-cov"]

    mocks = _prepare_test_cmd_mocks(cwd=cwd)
    clear_hudson_env(mocks)

    run_test_cmd_expect_system_exit(mocks)

    assert_pytest_was_invoked(mocks, cwd=cwd)
    assert_requirements_installed(mocks, expected_installed_reqs)

    # check that PyLint was not invoked
    assert not mocks["subprocess.Popen"].called


@pytest.mark.parametrize(["enable_hudson_mode"],
                         [[_enable_hudson_via_cmd_arg],
                          [_enable_hudson_via_environment]],
                         ids=["enable_hudson_via_cmd_arg",
                              "enable_hudson_via_environment"])
def test_run__hudson__runs_pylint_but_no_pylint_is_written(enable_hudson_mode):
    expected_installed_reqs = ["pytest", "pytest-cov", sentinel.linter_pkg]
    mocks = _prepare_test_cmd_mocks()
    enable_hudson_mode(mocks)

    run_test_cmd_expect_system_exit(mocks)

    assert_pytest_and_pylint_were_invoked(mocks)
    assert_requirements_installed(mocks, expected_installed_reqs)
    assert_no_pylint_was_written(mocks)


@pytest.mark.parametrize(["enable_hudson_mode"],
                         [[_enable_hudson_via_cmd_arg],
                          [_enable_hudson_via_environment]],
                         ids=["enable_hudson_via_cmd_arg",
                              "enable_hudson_via_environment"])
def test_run__hudson__writes_pylint_to_base_dir(enable_hudson_mode):
    cwd = _make_root_dir_from("<somewhere>")
    pylint_output = "Python detected, consider using Java or C/C++"

    expected_pylint_file_location = os.path.join(cwd, test.HUDSON_XML_PYLINT)
    expected_output = pylint_output + '\n'

    mocks = _prepare_test_cmd_mocks(cwd=cwd, pylint_output=pylint_output)
    enable_hudson_mode(mocks)

    run_test_cmd_expect_system_exit(mocks)

    assert_pytest_and_pylint_were_invoked(mocks)
    assert_pylint_was_written(mocks, expected_pylint_file_location,
                              expected_output)


@pytest.mark.parametrize(["enable_hudson_mode"],
                         [[_enable_hudson_via_cmd_arg],
                          [_enable_hudson_via_environment]],
                         ids=["enable_hudson_via_cmd_arg",
                              "enable_hudson_via_environment"])
def test_run__hudson__writes_pylint_to_original_dir(enable_hudson_mode):
    original_cwd = _make_root_dir_from("<original_non_base_dir>")
    dist_attrs = {"original_cwd": original_cwd}
    _test_hudson__pylint_is_written_to_non_base_dir(enable_hudson_mode,
                                                    original_cwd,
                                                    dist_attrs=dist_attrs)


@pytest.mark.parametrize(["enable_hudson_mode"],
                         [[_enable_hudson_via_cmd_arg_with_ws],
                          [_enable_hudson_via_environment_with_ws]],
                         ids=["enable_hudson_via_cmd_arg",
                              "enable_hudson_via_environment"])
def test_run__hudson__writes_pylint_to_workspace(enable_hudson_mode):
    original_cwd = _make_root_dir_from("<original_non_base_dir>")

    def enable_hudson_with_ws(mocks):
        enable_hudson_mode(mocks, original_cwd)

    _test_hudson__pylint_is_written_to_non_base_dir(enable_hudson_with_ws,
                                                    original_cwd)


def test_run__installs_all_extras():
    extras_require = {"paradise": ["ocean==2.5", "palms>5.5"],
                      "communism": ["Lenin==1.0", "hammer", "sickle"],
                      "confused": ["ocean==2.5", "hammer"]}

    expected_installed_reqs = ["pytest", "pytest-cov", "ocean==2.5", "palms>5.5",
                               "Lenin==1.0", "hammer", "sickle"]

    dist_attrs = {"extras_require": extras_require}

    mocks = _prepare_test_cmd_mocks()
    clear_hudson_env(mocks)

    run_test_cmd_expect_system_exit(mocks, dist_attrs=dist_attrs)

    assert_requirements_installed(mocks, expected_installed_reqs)
