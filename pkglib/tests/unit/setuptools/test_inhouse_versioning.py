import pkglib.setuptools  # monkeypatch; @UnusedImport # NOQA

from pkg_resources import parse_version
from zc.buildout import easy_install
from mock import patch

from pkglib.config import org

TEST_CONFIG = org.OrganisationConfig(third_party_build_prefix='acme')


def test_inhouse_version_is_between_upstream_versions():
    with patch('pkglib.setuptools.patches.inhouse_build_version.CONFIG', TEST_CONFIG):
        assert parse_version('1.0') < parse_version('1.0-acme1') < parse_version('1.0-final1')


def test_inhouse_version_is_final():
    with patch('pkglib.setuptools.patches.inhouse_build_version.CONFIG', TEST_CONFIG):
        assert easy_install._final_version(parse_version('1.0-acme1'))
