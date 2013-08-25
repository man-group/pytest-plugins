import sys
from setuptools.dist import Distribution

from mock import patch

from pkglib_testing.mock.subprocess import patch_subprocess, get_subprocess_mock
from pkglib.setuptools.command import cleanup

from helper import Pkg


def test_cleanup_filter_OK():
    dist = Distribution()
    cmd = cleanup.cleanup(dist)
    assert cmd.filter_victim('foo.egg')


def test_cleanup_filter_non_egg():
    dist = Distribution()
    cmd = cleanup.cleanup(dist)
    assert not cmd.filter_victim('foo')


def test_cleanup_filter_open_file():
    dist = Distribution()
    cmd = cleanup.cleanup(dist)
    cmd.open_files = [('1234', '/path/to/foo.egg')]
    assert not cmd.filter_open_files('foo.egg')


LSOF_OUT = """
12345   foo
67890   bar
"""


@patch_subprocess(get_subprocess_mock(LSOF_OUT, '', 0))
def test_get_open_files():
    dist = Distribution()
    cmd = cleanup.cleanup(dist)
    assert cmd.get_open_files() == [['12345', 'foo'], ['67890', 'bar']]


def test_find_victims():
    my_working_set = [
       Pkg('acme.foo', [], location='site-packages/acme.foo.egg'),
       Pkg('acme.bar', [], location='site-packages/acme.bar.egg'),
    ]

    class DummySite(object):
        def listdir(self):
            return [
                    'site-packages/acme.foo.egg',
                    'site-packages/acme.bar.egg',
                    'site-packages/acme.baz.egg',
                    'site-packages/acme.qux.egg',
                    'site-packages/acme.spam.pth',
             ]

    with patch.object(cleanup, 'working_set', my_working_set):
        with patch.object(sys, 'exec_prefix', 'site-packages'):
            dist = Distribution()
            cmd = cleanup.cleanup(dist)
            cmd.get_site_packages = lambda: DummySite()
            assert cmd.find_victims() == ['site-packages/acme.baz.egg',
                                          'site-packages/acme.qux.egg']
