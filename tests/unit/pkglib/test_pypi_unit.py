from mock import patch
import urllib2
import subprocess

from path import path

from pkglib.pypi import CluePyPiApi
from pkglib.manage import chdir
from pkglib.testing.pytest.util import pytest_funcarg__workspace
from pkglib.testing.mock.subprocess import patch_subprocess, get_subprocess_mock

from helper import mock_clue


def test_homepage():
    """ Api package homepage method test """
    pypi = CluePyPiApi('http://foo')
    assert pypi._pkg_home('acme.foo') == "http://foo/d/acme.foo"


def test_scrape_uri_from_clue():
    """ Tests the clue url scraper
    """
    pypi = CluePyPiApi('http://foo')
    with patch.object(urllib2, 'urlopen', mock_clue()):
        assert pypi.scrape_pkg_uri('http://dummy', 'acme.foo') == \
            'http://mysvn/acme.foo'


def test_get_mirror_dirname():
    pypi = CluePyPiApi('http://foo')
    assert pypi.get_mirror_dirname('foo') == 'f'
    assert pypi.get_mirror_dirname('acme.foo') == 'af'
    assert pypi.get_mirror_dirname('acme.foo.bar') == 'af'


def test_get_mirror_targets(workspace):
    pypi = CluePyPiApi('http://foo')
    dirs = [
            path('a') / 'acme.foo',
            path('a') / 'acme.bar',
            path('b') / 'baz',
            path('q') / 'qux',
            ]
    file_root = path(workspace.workspace)
    target_root = path('/path/to/dest')
    [(file_root / path(d)).makedirs() for d in dirs]

    # Test full list
    pkg_dirs, target_dirs = pypi.get_mirror_targets(file_root, target_root, None)
    assert set(pkg_dirs) == set([file_root / 'a' / 'acme.foo',
                                 file_root / 'a' / 'acme.bar',
                                 file_root / 'b' / 'baz',
                                 file_root / 'q' / 'qux'])
    assert set(target_dirs) == set([path('/path/to/dest/af'), path('/path/to/dest/ab'),
                                     path('/path/to/dest/b'), path('/path/to/dest/q')])

    # With target packages
    pkg_dirs, target_dirs = pypi.get_mirror_targets(file_root, target_root, ['acme.foo', 'qux'])
    assert set(pkg_dirs) == set([file_root / 'a' / 'acme.foo',
                                 file_root / 'q' / 'qux'])
    assert set(target_dirs) == set([path('/path/to/dest/af'), path('/path/to/dest/q')])


def test_mirror_eggs(workspace):
    pypi = CluePyPiApi('http://foo')
    dirs = [
            path('a') / 'acme.foo',
            path('a') / 'acme.bar',
            path('b') / 'baz',
            path('q') / 'qux',
            ]
    file_root = path(workspace.workspace)
    target_root = path('/path/to/dest')
    target_host = "blackmesa"
    [(file_root / d).makedirs() for d in dirs]
    for d in dirs:
        for v in [1.0, 2.0, 3.0]:
            egg = path(file_root / d / '%s-%0.1f.egg' % (d.basename(), v))
            egg.touch()

    # Disable the egg unpack stage for this test
    pypi.unpack_eggs = lambda i, j, k: None

    ssh_start = ['/usr/bin/ssh', 'blackmesa']
    rsync_start = ['/usr/bin/rsync', '-av', '--ignore-existing']

    @patch_subprocess(get_subprocess_mock('', '', 0))
    def do_test_one_pkg():
        pypi.mirror_eggs(file_root, target_host, target_root,
                         ['acme.foo'], 1)
        call_args = [i[0][0] for i in subprocess.Popen.call_args_list]
        print call_args

        assert call_args[0] == ssh_start + ['mkdir -p /path/to/dest/af']
        assert call_args[1][0:3] == rsync_start
        assert set(call_args[1][3:6]) == set(
            [file_root / 'a' / 'acme.foo' / 'acme.foo-1.0.egg',
            file_root / 'a' / 'acme.foo' / 'acme.foo-2.0.egg',
            file_root / 'a' / 'acme.foo' / 'acme.foo-3.0.egg'])
        assert call_args[1][6] == "blackmesa:/path/to/dest/af"

    @patch_subprocess(get_subprocess_mock('', '', 0))
    def do_test_two_pkg():
        pypi.mirror_eggs(file_root, target_host, target_root,
                         ['acme.foo', 'qux'], 1)
        call_args = [i[0][0] for i in subprocess.Popen.call_args_list]

        # not sure which order they turn up in, it doesnt matter so much
        assert call_args[0][:2] == ssh_start
        assert call_args[0][2].split()[:2] == ['mkdir', '-p']
        assert set(call_args[0][2].split()[-2:]) == set(['/path/to/dest/q', '/path/to/dest/af'])
        for call in call_args[1:]:
            assert call[0:3] == rsync_start
            letter = call[3].split(file_root + "/")[1][0]
            assert letter in ('a', 'q')
            if letter == 'q':
                assert set(call[3:6]) == set([
                    file_root / 'q' / 'qux' / 'qux-1.0.egg',
                    file_root / 'q' / 'qux' / 'qux-2.0.egg',
                    file_root / 'q' / 'qux' / 'qux-3.0.egg'])
                assert call[6] == "blackmesa:/path/to/dest/q"
            else:
                assert set(call[3:6]) == set([
                    file_root / 'a' / 'acme.foo' / 'acme.foo-1.0.egg',
                    file_root / 'a' / 'acme.foo' / 'acme.foo-2.0.egg',
                    file_root / 'a' / 'acme.foo' / 'acme.foo-3.0.egg'])
                assert call[6] == "blackmesa:/path/to/dest/af"

    do_test_one_pkg()
    do_test_two_pkg()


MIRROR_CONFIG = """
[mirrors]
keys = foo, bar

[foo]
hostname = foohost
target_dir = /path/to/foodir

[bar]
hostname = barhost
target_dir = /path/to/bardir
"""


def test_get_mirror_config(workspace):
    pypi = CluePyPiApi('http://foo')
    with chdir(workspace.workspace):
        with open('mirror.cfg', 'wb') as fp:
            fp.write(MIRROR_CONFIG)
        cfg = pypi.get_mirror_config('mirror.cfg')
        assert len(cfg) == 2
        for c in cfg:
            assert c['target_host'] in ('foohost', 'barhost')
            if c['target_host'] == 'foohost':
                assert c['target_dir'] == '/path/to/foodir'
            else:
                assert c['target_dir'] == '/path/to/bardir'
