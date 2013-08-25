# HACK: if the profile plugin is imported before the coverage plugin then all
# the top-level code in pkglib_testing.pytest.profile will be omitted from
# coverage, so force it to be reloaded within this test unit under coverage
import pkglib_testing.pytest.profile
reload(pkglib_testing.pytest.profile)
from pkglib_testing.pytest.profile import Profiling, pytest_addoption, pytest_configure
from mock import Mock, ANY, patch, sentinel


def test_creates_prof_dir():
    with patch('os.makedirs', side_effect=OSError) as makedirs:
        Profiling(False).pytest_sessionstart(Mock())
    makedirs.assert_called_with('prof')


def test_hooks_pyfunc_call():
    assert getattr(Profiling.pytest_pyfunc_call, 'tryfirst')
    multicall, pyfuncitem, plugin = Mock(), Mock(), Profiling(False)
    pyfuncitem.name.__add__ = Mock()
    with patch('os.path.join', return_value=sentinel.join):
        with patch('pkglib_testing.pytest.profile.cProfile') as cProfile:
            plugin.pytest_pyfunc_call(multicall, pyfuncitem)
    assert cProfile.runctx.called
    args, kwargs = cProfile.runctx.call_args
    assert kwargs['filename'] == sentinel.join
    assert not multicall.execute.called
    eval(*args)
    assert multicall.execute.called
    assert plugin.profs == [sentinel.join]


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
    with patch('pkglib_testing.pytest.profile.Profiling') as Profiling:
        pytest_configure(config)
    config.pluginmanager.register.assert_called_with(Profiling.return_value)
