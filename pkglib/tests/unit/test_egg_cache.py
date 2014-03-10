from mock import patch

from pkglib import config
from pkglib.egg_cache import get_egg_cache_paths, get_dev_egg_cache_paths


def test_get_egg_cache_paths():
    with patch('pkglib.egg_cache.CONFIG',
                config.OrganisationConfig(installer_search_path=['/usr'])):
        assert get_egg_cache_paths() == ['/usr']

    with patch('pkglib.egg_cache.CONFIG',
                config.OrganisationConfig(installer_search_path=['/usr', '/bin'])):
        assert get_egg_cache_paths() == ['/usr', '/bin']


def test_get_dev_egg_cache_paths():
    with patch('pkglib.egg_cache.CONFIG',
                config.OrganisationConfig(installer_dev_search_path=['/usr'])):
        assert get_dev_egg_cache_paths() == ['/usr']
        
    with patch('pkglib.egg_cache.CONFIG',
                config.OrganisationConfig(installer_dev_search_path=['/usr', '/bin'])):
        assert get_dev_egg_cache_paths() == ['/usr', '/bin']
