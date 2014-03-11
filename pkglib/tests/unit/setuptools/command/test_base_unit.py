from setuptools.dist import Distribution
from setuptools import Command
from mock import patch

from pkglib.config import org
from pkglib.setuptools.command import base, develop, pyinstall, upload, register

TEST_CONFIG = org.OrganisationConfig(pypi_variant=None)


class _TestCmd(Command, base.CommandMixin):
    user_options = [('foo', None, 'xxx'), ('bar', None, 'xxx')]

    def initialize_options(self):
        self.foo = 1
        self.bar = 2

    def finalize_options(self):
        pass


def get_cmd():
    dist = Distribution({'name': 'acme.foo'})
    cmd = _TestCmd(dist)
    return cmd


def test_get_option_list():
    cmd = get_cmd()
    assert cmd.get_option_list() == [('foo', 1), ('bar', 2)]


def test_maybe_add_simple_index_empty():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop.develop(dist)
        assert cmd.maybe_add_simple_index('') == ''


def test_maybe_add_simple_index_already_there():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop.develop(dist)
        assert cmd.maybe_add_simple_index('http://foo/simple') == 'http://foo/simple'
        assert cmd.maybe_add_simple_index('http://foo/simple/') == 'http://foo/simple/'


def test_maybe_add_simple_index_develop():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = develop.develop(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_pyinstall():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = pyinstall.pyinstall(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_upload():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = upload.upload(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'


def test_maybe_add_simple_index_register():
    with patch.object(base, 'CONFIG', TEST_CONFIG):
        dist = Distribution()
        cmd = register.register(dist)
        assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'
