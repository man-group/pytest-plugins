import sys

from setuptools.dist import Distribution
from mock import patch

from pkglib.setuptools.command import clean
from pkglib_testing.mocking.subprocess import patch_subprocess, get_subprocess_mock

from .runner import Pkg, patch_obj


def test_is_ignored_directory_ok():
    t = clean.clean(Distribution())
    assert not t._is_ignored_directory('not and egg or svn')


def test_svn_is_ignored_directory():
    t = clean.clean(Distribution())
    assert t._is_ignored_directory('.svn')


def test_egg_is_ignored_directory1():
    t = clean.clean(Distribution())
    assert t._is_ignored_directory('ANYthing12.egg')


def test_egg_is_ignored_directory2():
    t = clean.clean(Distribution())
    assert t._is_ignored_directory('ANY_thing12.egg')


def test_egg_is_ignored_directory3():
    t = clean.clean(Distribution())
    assert t._is_ignored_directory('ANY-thing12.egg')


def test_cleanup_filter_OK():
    dist = Distribution()
    cmd = clean.clean(dist)
    assert cmd.filter_victim('foo.egg')


def test_cleanup_filter_non_egg():
    dist = Distribution()
    cmd = clean.clean(dist)
    assert not cmd.filter_victim('foo')


def test_cleanup_filter_open_file():
    dist = Distribution()
    cmd = clean.clean(dist)
    cmd.open_files = [('1234', '/path/to/foo.egg')]
    assert not cmd.filter_open_files('foo.egg')



LSOF_OUT = """
12345   foo
67890   bar
"""


@patch_subprocess(get_subprocess_mock(LSOF_OUT, '', 0))
def test_get_open_files():
    dist = Distribution()
    cmd = clean.clean(dist)
    assert cmd.get_open_files() == [['12345', 'foo'], ['67890', 'bar']]


def test_find_victims():
    my_working_set = [
       Pkg('acme.foo', [], location='site-packages/acme.foo.egg'),
       Pkg('acme.bar', [], location='site-packages/acme.bar.egg'),
    ]

    def get_site_packages():
        return ['site-packages/acme.foo.egg',
                'site-packages/acme.bar.egg',
                'site-packages/acme.baz.egg',
                'site-packages/acme.qux.egg',
                'site-packages/acme.spam.pth']

    with patch_obj(clean, 'working_set', my_working_set):
        with patch_obj(sys, 'exec_prefix', 'site-packages'):
            dist = Distribution()
            cmd = clean.clean(dist)
            cmd.get_site_packages = lambda: ""
            with patch("os.listdir", return_value=get_site_packages()):
                assert cmd.find_victims() == ['site-packages/acme.baz.egg',
                                              'site-packages/acme.qux.egg']
