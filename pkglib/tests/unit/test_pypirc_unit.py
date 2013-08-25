from setuptools.dist import Distribution

from mock import patch

from pkglib import config
from pkglib.setuptools.command.develop import develop
from pkglib.setuptools.command.pyinstall import pyinstall
from pkglib.setuptools.command.upload import upload
from pkglib.setuptools.command.register import register
from pkglib.setuptools.command import base

TEST_CONFIG = config.OrganisationConfig(pypi_variant=None)


def test_maybe_add_simple_index_empty():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop(dist)
        assert cmd.maybe_add_simple_index('') == ''


def test_maybe_add_simple_index_already_there():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop(dist)
        assert cmd.maybe_add_simple_index('http://foo/simple') == 'http://foo/simple'
        assert cmd.maybe_add_simple_index('http://foo/simple/') == 'http://foo/simple/'


def test_maybe_add_simple_index_develop():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_pyinstall():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = pyinstall(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_upload():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = upload(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'


def test_maybe_add_simple_index_register():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = register(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'
