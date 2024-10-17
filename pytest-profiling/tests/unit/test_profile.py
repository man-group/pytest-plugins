# HACK: if the profile plugin is imported before the coverage plugin then all
# the top-level code in pytest_profiling will be omitted from
# coverage, so force it to be reloaded within this test unit under coverage

import os.path
from six.moves import reload_module  # @UnresolvedImport

import pytest_profiling

reload_module(pytest_profiling)

import os
import subprocess

import pytest
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
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0)
    )
    popen2 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0)
    )
    with patch("pstats.Stats"):
        with patch("subprocess.Popen", side_effect=[popen1, popen2]) as popen:
            plugin.pytest_sessionfinish(Mock(), Mock())
    calls = popen.mock_calls
    assert calls[0] == call(
        ["dot", "-Tsvg", "-o", f"{os.getcwd()}/prof/combined.svg"],
        stdin=subprocess.PIPE,
        shell=True,
    )
    assert calls[1] == call(
        ["/somewhere/gprof2dot", "-f", "pstats", f"{os.getcwd()}/prof/combined.prof"],
        stdout=popen1.stdin,
        shell=True,
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
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0)
    )
    popen2 = Mock(
        communicate=Mock(return_value=[None, None]), poll=Mock(return_value=0)
    )
    with patch("pstats.Stats"):
        with patch("subprocess.Popen", side_effect=[popen1, popen2]):
            plugin.pytest_sessionfinish(Mock(), Mock())
        plugin.pytest_terminal_summary(terminalreporter)
    assert "SVG" in terminalreporter.write.call_args[0][0]


def test_adds_options():
    parser = pytest.Parser()
    pytest_addoption(parser)
    group = parser.getgroup("Profiling")
    options = {
        option.dest: option for option in group.options
    }
    assert set(options.keys()) == {"profile", "profile_svg", "pstats_dir", "element_number", "strip_dirs"}
    assert options["profile"]._attrs["action"] == "store_true"
    assert options["profile_svg"]._attrs["action"] == "store_true"
    assert options["pstats_dir"]._attrs["nargs"] == 1
    assert options["strip_dirs"]._attrs["action"] == "store_true"
    assert options["element_number"]._attrs["action"] == "store"
    assert options["element_number"]._attrs["default"] == 20


def test_configures():
    config = Mock(getvalue=lambda x: x == "profile")
    with patch("pytest_profiling.Profiling") as Profiling:
        pytest_configure(config)
    config.pluginmanager.register.assert_called_with(Profiling.return_value)


def test_clean_filename():
    assert pytest_profiling.clean_filename("a:b/c\256d") == "a_b_c_d"
