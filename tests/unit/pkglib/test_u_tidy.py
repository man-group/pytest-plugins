from pkglib.setuptools.command import tidy
from setuptools.dist import Distribution


def test_is_ignored_directory_ok():
    t = tidy.tidy(Distribution())
    assert not t._is_ignored_directory('not and egg or svn')


def test_svn_is_ignored_directory():
    t = tidy.tidy(Distribution())
    assert t._is_ignored_directory('.svn')


def test_egg_is_ignored_directory1():
    t = tidy.tidy(Distribution())
    assert t._is_ignored_directory('ANYthing12.egg')


def test_egg_is_ignored_directory2():
    t = tidy.tidy(Distribution())
    assert t._is_ignored_directory('ANY_thing12.egg')


def test_egg_is_ignored_directory3():
    t = tidy.tidy(Distribution())
    assert t._is_ignored_directory('ANY-thing12.egg')

