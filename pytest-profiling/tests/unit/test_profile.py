# HACK: if the profile plugin is imported before the coverage plugin then all
# the top-level code in pytest_profiling will be omitted from
# coverage, so force it to be reloaded within this test unit under coverage

import os.path
from six.moves import reload_module  # @UnresolvedImport

import pytest_profiling

reload_module(pytest_profiling)

import os
import subprocess

from pytest_profiling import Profiling, pytest_addoption, pytest_configure

try:
    from unittest.mock import Mock, ANY, patch, sentinel, call
except ImportError:
    # python 2
    from mock import Mock, ANY, patch, sentinel


def test_creates_prof_dir():
    with patch("os.makedirs", side_effect=OSError) as makedirs:
        Profiling(False).pytest_sessionstart(Mock())
    makedirs.assert_called_with("prof")


def test_combines_profs():
    plugin = Profiling(False)
    plugin.profs = [sentinel.prof0, sentinel.prof1]
    with patch("pstats.Stats") as Stats:
        plugin.pytest_sessionfinish(Mock(), Mock())
    Stats.assert_called_once_with(sentinel.prof0)
    Stats.return_value.add.assert_called_once_with(sentinel.prof1)
    assert Stats.return_value.dump_stats.called


def test_generates_svg():
    plugin = Profiling(True)
    plugin.gprof2dot = "/somewhere/gprof2dot"
    plugin.profs = [sentinel.prof]
    popen1 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0), returncode=0
    )
    popen2 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0), returncode=0
    )
    with patch("pstats.Stats"):
        with patch("subprocess.Popen") as popen:
            popen.return_value.__enter__.side_effect = [popen1, popen2]
            plugin.pytest_sessionfinish(Mock(), Mock())
    popen.assert_any_call(
        ["dot", "-Tsvg", "-o", f"{os.getcwd()}/prof/combined.svg"],
        stdin=popen1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    popen.assert_any_call(
        ["/somewhere/gprof2dot", "-f", "pstats", f"{os.getcwd()}/prof/combined.prof"],
        stdout=subprocess.PIPE,
    )


def test_writes_summary():
    plugin = Profiling(False)
    plugin.profs = [sentinel.prof]
    terminalreporter, stats = Mock(), Mock()
    with patch("pstats.Stats", return_value=stats) as Stats:
        plugin.pytest_sessionfinish(Mock(), Mock())
        plugin.pytest_terminal_summary(terminalreporter)
    combined = os.path.abspath(
        os.path.join(os.path.curdir, "prof", "combined.prof"))
    assert "Profiling" in terminalreporter.write.call_args[0][0]
    Stats.assert_called_with(combined, stream=terminalreporter)


def test_writes_summary_svg():
    plugin = Profiling(True)
    plugin.profs = [sentinel.prof]
    terminalreporter = Mock()
    popen1 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0), returncode=0
    )
    popen2 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0), returncode=0
    )
    with patch("pstats.Stats"):
        with patch("subprocess.Popen") as popen:
            popen.return_value.__enter__.side_effect = [popen1, popen2]
            plugin.pytest_sessionfinish(Mock(), Mock())
        plugin.pytest_terminal_summary(terminalreporter)
    assert "SVG" in terminalreporter.write.call_args[0][0]


def test_adds_options():
    parser = Mock()
    pytest_addoption(parser)
    parser.getgroup.assert_called_with("Profiling")
    group = parser.getgroup.return_value
    group.addoption.assert_any_call("--profile", action="store_true", help=ANY)
    group.addoption.assert_any_call("--profile-svg", action="store_true", help=ANY)


def test_configures():
    config = Mock(getvalue=lambda x: x == "profile")
    with patch("pytest_profiling.Profiling") as Profiling:
        pytest_configure(config)
    config.pluginmanager.register.assert_called_with(Profiling.return_value)


def test_clean_filename():
    assert pytest_profiling.clean_filename("a:b/c\256d") == "a_b_c_d"
