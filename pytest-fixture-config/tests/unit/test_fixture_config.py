import pytest
from six.moves import reload_module

# HACK: if the plugin is imported before the coverage plugin then all
# the top-level code will be omitted from coverage, so force it to be
# reloaded within this unit test under coverage
import pytest_fixture_config
reload_module(pytest_fixture_config)

from pytest_fixture_config import Config

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

