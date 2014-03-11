""" Unit tests for pkglib.manage
"""
import os

import mock

from pkglib import util, config
from pkglib.config import org

pytest_plugins = ['pkglib_testing.pytest.util']


TEST_CONFIG = org.OrganisationConfig(namespaces=['acme'],
                                     namespace_separator='.')


def test_is_inhouse_package():
    with mock.patch.object(util, 'CONFIG', TEST_CONFIG):
        assert util.is_inhouse_package('acme.foo')
        assert not util.is_inhouse_package('foo')


def test_is_dev_version():
    assert util.is_dev_version('1.2.3.dev1')
    assert util.is_dev_version('1.2.3.dev4')
    assert not util.is_dev_version('1.2.3')
    assert not util.is_dev_version('1.2.3dev4')


def test_is_strict_dev_version():
    assert util.is_strict_dev_version('0.0.dev1')
    assert util.is_strict_dev_version('0.0.dev4')
    assert not util.is_strict_dev_version('1.2.3')
    assert not util.is_strict_dev_version('1.2.3dev4')
    assert not util.is_strict_dev_version('1.0.0.dev4')


def test_get_namespace_packages():
    with mock.patch.object(util, 'CONFIG', TEST_CONFIG):
        assert util.get_namespace_packages('') == []
        assert util.get_namespace_packages('foo') == []
        assert util.get_namespace_packages('foo.bar') == ['foo']
        assert util.get_namespace_packages('foo.bar.baz') == ['foo', 'foo.bar']
        assert util.get_namespace_packages('foo.bar.baz.qux') == ['foo', 'foo.bar', 'foo.bar.baz']
