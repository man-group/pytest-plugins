import pytest
from six.moves import reload_module

# HACK: if the plugin is imported before the coverage plugin then all
# the top-level code will be omitted from coverage, so force it to be
# reloaded within this unit test under coverage
import pytest_fixture_config
reload_module(pytest_fixture_config)

from pytest_fixture_config import Config, requires_config, yield_requires_config

class DummyConfig(Config):
    __slots__ = ('foo', 'bar')


def test_config_update():
    cfg = DummyConfig(foo=1,
                      bar=2
                      )
    cfg.update({"foo": 10, "bar":20})
    assert cfg.foo == 10
    assert cfg.bar == 20
    with pytest.raises(ValueError):
        cfg.update({"baz": 30})


CONFIG1 = DummyConfig(foo=None, bar=1)

@requires_config(CONFIG1, ('foo', 'bar'))
@pytest.fixture
def a_fixture(request):
    raise ValueError('Should not run')


def test_requires_config_skips(a_fixture):
    raise ValueError('Should not run')


@requires_config(CONFIG1, ('bar',))
@pytest.fixture
def another_fixture(request):
    return 'xxxx'


def test_requires_config_doesnt_skip(another_fixture):
    assert another_fixture == 'xxxx'
    
    

@yield_requires_config(CONFIG1, ('foo', 'bar'))
@pytest.yield_fixture
def yet_another_fixture():
    raise ValueError('Should also not run')
    yield 'yyyy'


def test_yield_requires_config_skips(yet_another_fixture):
    raise ValueError('Should also not run')


@yield_requires_config(CONFIG1, ('bar',))
@pytest.yield_fixture
def yet_some_other_fixture():
    yield 'yyyy'


def test_yield_requires_config_doesnt_skip(yet_some_other_fixture):
    assert yet_some_other_fixture == 'yyyy'
