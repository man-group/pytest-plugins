# HACK: if the profile plugin is imported before the coverage plugin then all
# the top-level code in pytest_profiling will be omitted from
# coverage, so force it to be reloaded within this test unit under coverage

from six.moves import reload_module  # @UnresolvedImport

import pytest_profiling
reload_module(pytest_profiling)

from pytest_profiling import Profiling, pytest_addoption, pytest_configure
from mock import Mock, ANY, patch, sentinel


def test_creates_prof_dir():
    with patch('os.makedirs', side_effect=OSError) as makedirs:
        Profiling(False).pytest_sessionstart(Mock())
    makedirs.assert_called_with('prof')


def test_combines_profs():
    plugin = Profiling(False)
    plugin.profs = [sentinel.prof0, sentinel.prof1]
    with patch('pstats.Stats') as Stats:
        plugin.pytest_sessionfinish(Mock(), Mock())
    Stats.assert_called_once_with(sentinel.prof0)
    Stats.return_value.add.assert_called_once_with(sentinel.prof1)
    assert Stats.return_value.dump_stats.called


def test_generates_svg():
    plugin = Profiling(True)
    plugin.profs = [sentinel.prof]
    with patch('pstats.Stats'):
        with patch('pipes.Template') as Template:
            plugin.pytest_sessionfinish(Mock(), Mock())
    assert any('gprof2dot' in args[0][0] for args in Template.return_value.append.call_args_list)
    assert Template.return_value.copy.called


def test_writes_summary():
    plugin = Profiling(False)
    plugin.profs = [sentinel.prof]
    terminalreporter, stats = Mock(), Mock()
    with patch('pstats.Stats', return_value=stats) as Stats:
        plugin.pytest_sessionfinish(Mock(), Mock())
        plugin.pytest_terminal_summary(terminalreporter)
    assert 'Profiling' in terminalreporter.write.call_args[0][0]
    assert Stats.called_with(stats, stream=terminalreporter)


def test_writes_summary_svg():
    plugin = Profiling(True)
    plugin.profs = [sentinel.prof]
    terminalreporter = Mock()
    with patch('pstats.Stats'):
        with patch('pipes.Template'):
            plugin.pytest_sessionfinish(Mock(), Mock())
        plugin.pytest_terminal_summary(terminalreporter)
    assert 'SVG' in terminalreporter.write.call_args[0][0]


def test_adds_options():
    parser = Mock()
    pytest_addoption(parser)
    parser.getgroup.assert_called_with('Profiling')
    group = parser.getgroup.return_value
    group.addoption.assert_any_call('--profile', action='store_true', help=ANY)
    group.addoption.assert_any_call('--profile-svg', action='store_true', help=ANY)


def test_configures():
    config = Mock(getvalue=lambda x: x == 'profile')
    with patch('pytest_profiling.Profiling') as Profiling:
        pytest_configure(config)
    config.pluginmanager.register.assert_called_with(Profiling.return_value)


def test_clean_filename():
    assert pytest_profiling.clean_filename('a:b/c\256d') == 'a_b_c_d'
