from setuptools.dist import Distribution

from pkglib.setuptools.command.develop import develop
from pkglib.setuptools.command.pyinstall import pyinstall
from pkglib.setuptools.command.upload import upload
from pkglib.setuptools.command.register import register


def test_maybe_add_simple_index_empty():
    dist = Distribution()
    cmd = develop(dist)
    assert cmd.maybe_add_simple_index('') == ''


def test_maybe_add_simple_index_already_there():
    dist = Distribution()
    cmd = develop(dist)
    assert cmd.maybe_add_simple_index('http://foo/simple') == 'http://foo/simple'
    assert cmd.maybe_add_simple_index('http://foo/simple/') == 'http://foo/simple/'


def test_maybe_add_simple_index_develop():
    dist = Distribution()
    cmd = develop(dist)
    assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_pyinstall():
    dist = Distribution()
    cmd = pyinstall(dist)
    assert cmd.maybe_add_simple_index('http://foo') == 'http://foo/simple'


def test_maybe_add_simple_index_upload():
    dist = Distribution()
    cmd = upload(dist)
    assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'


def test_maybe_add_simple_index_register():
    dist = Distribution()
    cmd = register(dist)
    assert cmd.maybe_add_simple_index('http://foo') == 'http://foo'
