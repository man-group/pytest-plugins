""" Unit tests for pkglib.manage
"""
import os

import mock

from pkglib import manage, config

pytest_plugins = ['pkglib_testing.pytest.util']


TEST_CONFIG = config.OrganisationConfig(namespaces=['acme'],
                                      namespace_separator='.')


def test_chdir():
    here = os.getcwd()
    with manage.chdir('/bin'):
        assert os.getcwd() == '/bin'
    assert os.getcwd() == here


def test_set_home():
    home = os.environ['HOME']
    with manage.set_home('/tmp'):
        assert os.environ['HOME'] == '/tmp'
    assert os.environ['HOME'] == home


def test_is_inhouse_package():
    with mock.patch.object(manage, 'CONFIG', TEST_CONFIG):
        assert manage.is_inhouse_package('acme.foo')
        assert not manage.is_inhouse_package('foo')


def test_is_dev_version():
    assert manage.is_dev_version('1.2.3.dev1')
    assert manage.is_dev_version('1.2.3.dev4')
    assert not manage.is_dev_version('1.2.3')
    assert not manage.is_dev_version('1.2.3dev4')


def test_is_strict_dev_version():
    assert manage.is_strict_dev_version('0.0.dev1')
    assert manage.is_strict_dev_version('0.0.dev4')
    assert not manage.is_strict_dev_version('1.2.3')
    assert not manage.is_strict_dev_version('1.2.3dev4')
    assert not manage.is_strict_dev_version('1.0.0.dev4')


def test_get_inhouse_dependencies(workspace):
    with mock.patch.object(manage, 'CONFIG', TEST_CONFIG):
        with open(os.path.join(workspace.workspace, 'setup.cfg'), 'wb') as fp:
            fp.write("""[metadata]
name = acme.foo
version = 2.3.5
install_requires =
    scipy
    numpy
    acme.a
    acme.b>=1.0.0
    acme.c<3.0
""")
        result = [i for i in
                  manage.get_inhouse_dependencies(workspace.workspace)]
        assert result == ['acme.a', 'acme.b', 'acme.c']


def test_get_namespace_packages():
    with mock.patch.object(manage, 'CONFIG', TEST_CONFIG):
        assert manage.get_namespace_packages('') == []
        assert manage.get_namespace_packages('foo') == []
        assert manage.get_namespace_packages('foo.bar') == ['foo']
        assert manage.get_namespace_packages('foo.bar.baz') == ['foo', 'foo.bar']
        assert manage.get_namespace_packages('foo.bar.baz.qux') == ['foo', 'foo.bar', 'foo.bar.baz']
