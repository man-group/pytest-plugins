import os
import subprocess

import pkglib  # @UnusedImport setup moves

from six.moves import (cStringIO,  # @UnresolvedImport
                       HTTPError, HTTPBasicAuthHandler, addinfourl, ExitStack)  # @UnresolvedImport # NOQA
#
# try:
#     from contextlib import ExitStack
# except ImportError:
#     from contextlib2 import ExitStack

_open_director = HTTPBasicAuthHandler.__module__ + '.OpenerDirector'
_open_director_open = _open_director + '.open'


from mock import patch
from pytest import raises

from pkglib_testing.mocking.subprocess import patch_subprocess, get_subprocess_mock

from pkglib.pypi.clue import CluePyPIAPI
from pkglib.pypi.pypirc import PyPIRC
from pkglib.errors import UserError

from .helper import mock_clue, _patch_open


def test_homepage():
    """ Api package homepage method test """
    pypi = CluePyPIAPI('http://example.com')
    assert pypi._pkg_home('acme.foo') == "http://example.com/d/acme.foo"


def test_scrape_uri_from_clue():
    """ Tests the clue url scraper
    """
    pypi = CluePyPIAPI('http://example.com')
    with patch('pkglib.pypi.clue.urllib2.urlopen', mock_clue()):
        assert pypi.scrape_pkg_uri('http://dummy', 'acme.foo') == \
            'http://mysvn/acme.foo'


def test_get_mirror_dirname():
    pypi = CluePyPIAPI('http://example.com')
    assert pypi.get_mirror_dirname('foo') == 'f'
    assert pypi.get_mirror_dirname('acme.foo') == 'af'
    assert pypi.get_mirror_dirname('acme.foo.bar') == 'af'


def _test_get_mirror_targets(dirs,
                             expected_pkg_dirs,
                             expected_target_dirs,
                             namespace_packages=None,):
    pypi = CluePyPIAPI('http://example.com')
    src_root = "/src"
    target_root = '/path/to/dest'

    def walk_mock(_):
        data = [(src_root, dirs.keys(), [])]
        for d in dirs:
            data.append((os.path.join(src_root, d), dirs[d], []))
        return data

    # Test full list
    with ExitStack() as stack:
        stack.enter_context(patch("os.walk", side_effect=walk_mock))
        stack.enter_context(patch("os.path.isdir", return_value=True))

        pkg_dirs, target_dirs = pypi.get_mirror_targets(src_root, target_root,
                                                        namespace_packages)

    assert set(pkg_dirs) == set(os.path.join(src_root, p)
                                for p in expected_pkg_dirs)
    assert set(target_dirs) == set(os.path.join(target_root, d)
                                   for d in expected_target_dirs)


def test_get_mirror_targets__no_namespace():
    dirs = {'a': ['acme.foo', 'acme.bar'],
            'b': ['baz'],
            'q': ['qux']}

    _test_get_mirror_targets(dirs,
                             [os.path.join("a", "acme.foo"),
                              os.path.join("a", "acme.bar"),
                              os.path.join("b", "baz"),
                              os.path.join("q", "qux")],
                             ["af", "ab", "b", "q"],)


def test_get_mirror_targets__with_namespace():
    dirs = {'a': ['acme.foo', 'acme.bar'],
            'b': ['baz'],
            'q': ['qux']}

    _test_get_mirror_targets(dirs,
                             [os.path.join("a", "acme.foo"),
                              os.path.join("q", "qux")],
                             ["af", "q"],
                             namespace_packages=['acme.foo', 'qux'])


def assert_eggs_mirrored(popen_mock, src, target, host, eggs):
    ssh_start = ['/usr/bin/ssh', 'dlonfoobar']
    rsync_start = ['/usr/bin/rsync', '-av', '--ignore-existing']

    call_args = [i[0][0] for i in popen_mock.call_args_list]

    unique_namespaces = set(["".join(p[0].lower() for p in
                                     os.path.basename(e).split('.')[:-2])
                             for e in eggs])
    known_letters = [ns[0] for ns in unique_namespaces]
    expected_mkdir_args = [os.path.join(target, d)
                           for d in unique_namespaces]
    assert call_args[0][:len(ssh_start)] == ssh_start
    assert call_args[0][len(ssh_start)].startswith("mkdir -p ")
    actual_mkdir_args = call_args[0][len(ssh_start)][len("mkdir -p "):]
    actual_mkdir_args = [arg.strip() for arg in actual_mkdir_args.split()]

    assert sorted(actual_mkdir_args) == sorted(expected_mkdir_args)

    processed = set([])
    remaining = eggs[:]
    for call in call_args[1:]:
        assert call[0:3] == rsync_start

        letter = call[3].split(src + os.path.sep)[1][0]
        assert letter in known_letters

        for egg in call[3:-1]:
            assert os.path.basename(egg) in remaining
            assert egg not in processed

            remaining.remove(os.path.basename(egg))
            processed.add(egg)

            ns = "".join(p[0].lower()
                         for p in os.path.basename(egg).split('.')[:-2])
            assert call[6] == "%s:%s" % (host, os.path.join(target, ns))


def _test_mirror_eggs(dirs, target_pkgs=None):
    pypi = CluePyPIAPI('http://example.com')
    src_root = "/src"
    target_root = '/path/to/dest'
    target_host = "dlonfoobar"

    eggs_by_pkg = dict((p, ['%s-%0.1f.egg' % (p, v) for v in [1.0, 2.0, 3.0]])
                       for d in dirs for p in dirs[d])

    eggs_by_path = dict((os.path.join(src_root,
                                      [d for d in dirs
                                       if p in dirs[d]][0], p), egg)
                        for p, egg in eggs_by_pkg.items())

    # Disable the egg unpack stage for this test
    pypi.unpack_eggs = lambda _i, _j, _k: None

    def walk_mock(_):
        data = [(src_root, dirs.keys(), [])]
        for d in dirs:
            data.append((os.path.join(src_root, d), dirs[d], []))
        return data

    def is_file_mock(f):
        return os.path.basename(f) in eggs_by_path.get(os.path.dirname(f), {})

    @patch_subprocess(get_subprocess_mock('', '', 0))
    def run():
        pypi.mirror_eggs(src_root, target_host, target_root, target_pkgs, 1)
        return subprocess.Popen

    with ExitStack() as stack:
        ec = stack.enter_context
        ec(patch("os.walk", side_effect=walk_mock))
        ec(patch("os.path.isdir", return_value=True))
        ec(patch("os.listdir", side_effect=lambda d: eggs_by_path[d]))
        ec(patch("os.path.isfile", side_effect=is_file_mock))

        return run(), src_root, target_root, target_host, eggs_by_pkg


def test_mirror_eggs__no_packages():
    dirs = {}

    popen_mock, _, _, _, eggs_by_pkg = _test_mirror_eggs(dirs)

    assert not popen_mock.called
    assert len(eggs_by_pkg) == 0


def test_mirr_eggs__one_package():
    dirs = {'a': ['acme.foo', 'acme.bar'],
            'b': ['baz'],
            'q': ['qux']}

    target_packages = ["acme.foo"]

    res = _test_mirror_eggs(dirs, target_pkgs=target_packages)
    popen_mock, src, target, host, eggs_by_pkg = res

    assert_eggs_mirrored(popen_mock, src, target, host,
                         [egg for p in ["acme.foo"]
                          for egg in eggs_by_pkg[p]])


def test_mirr_eggs__two_packages():
    dirs = {'a': ['acme.foo', 'acme.bar'],
            'b': ['baz'],
            'q': ['qux']}

    target_packages = ['acme.foo', 'qux']

    res = _test_mirror_eggs(dirs, target_pkgs=target_packages)
    popen_mock, src, target, host, eggs_by_pkg = res

    assert_eggs_mirrored(popen_mock, src, target, host,
                         [egg for p in ['acme.foo', 'qux']
                          for egg in eggs_by_pkg[p]])


def test_mirror_eggs__all_packages():
    dirs = {'a': ['acme.foo', 'acme.bar'],
            'b': ['baz'],
            'q': ['qux']}

    popen_mock, src, target, host, eggs_by_pkg = _test_mirror_eggs(dirs)
    assert_eggs_mirrored(popen_mock, src, target, host,
                         [egg for p in ["acme.foo", "acme.bar", "baz", "qux"]
                          for egg in eggs_by_pkg[p]])


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


def test_get_mirror_config():
    pypi = CluePyPIAPI('http://example.com')

    mirror_cfg = cStringIO(MIRROR_CONFIG)
    file_dict = {'mirror.cfg': mirror_cfg}
    with ExitStack() as stack:
        stack.enter_context(_patch_open(file_dict=file_dict))
        stack.enter_context(patch("os.path.isfile", return_value=True))

        cfg = pypi.get_mirror_config('mirror.cfg')
        assert len(cfg) == 2
        for c in cfg:
            assert c['target_host'] in ('foohost', 'barhost')
            if c['target_host'] == 'foohost':
                assert c['target_dir'] == '/path/to/foodir'
            else:
                assert c['target_dir'] == '/path/to/bardir'


def test_validate_credentials():
    pypirc = PyPIRC()
    pypirc.set_server_username('http://sentinel.uri', 'Aladdin')  # RFC 1945
    pypirc.set_server_password('http://sentinel.uri', 'open sesame')
    bad_request = HTTPError('http://sentinel.uri', 400, 'Bad Request', {},
                            cStringIO(''))
    with patch(_open_director) as OpenerDirector:
        OpenerDirector.return_value.open.side_effect = bad_request
        pypirc.validate_credentials('http://sentinel.uri')
    request = next(req for (req,), _
                   in OpenerDirector.return_value.open.call_args_list)
    assert request.get_method() == 'GET'
    assert request.get_full_url() == 'http://sentinel.uri?%3Aaction=file_upload'
    auth = next(handler for (handler,), _
                in OpenerDirector.return_value.add_handler.call_args_list if
                isinstance(handler, HTTPBasicAuthHandler))
    assert (auth.passwd.find_user_password('pypi', 'http://sentinel.uri?%3A'
                                           'action=file_upload') ==
            ('Aladdin', 'open sesame'))


def test_validate_credentials_raises_user_error_on_unauthorized():
    pypirc = PyPIRC()
    pypirc.set_server_username('http://sentinel.uri', 'Aladdin')  # RFC 1945
    pypirc.set_server_password('http://sentinel.uri', 'open sesame')
    unauthorized = HTTPError('http://sentinel.uri', 401, 'basic auth failed',
                             {}, None)
    with patch(_open_director_open, side_effect=unauthorized):
        with raises(UserError) as exc:
            pypirc.validate_credentials('http://sentinel.uri')
    assert exc.value.msg == UserError('Invalid PyPi credentials',
                                      'http://sentinel.uri',
                                      'basic auth failed').msg


def test_validate_credentials_raises_on_unexpected_error():
    pypirc = PyPIRC()
    pypirc.set_server_username('http://sentinel.uri', 'Aladdin')  # RFC 1945
    pypirc.set_server_password('http://sentinel.uri', 'open sesame')
    internal_error = HTTPError('http://sentinel.uri', 500,
                               'Internal Server Error', {}, cStringIO('oops'))
    with patch(_open_director_open, side_effect=internal_error):
        with raises(IOError) as exc:
            pypirc.validate_credentials('http://sentinel.uri')
    assert repr(exc.value) == repr(IOError('Unexpected status from PyPi',
                                           'http://sentinel.uri', 500,
                                           'Internal Server Error: oops'))


def test_validate_credentials_raises_on_unexpected_success():
    pypirc = PyPIRC()
    pypirc.set_server_username('http://sentinel.uri', 'Aladdin')  # RFC 1945
    pypirc.set_server_password('http://sentinel.uri', 'open sesame')
    success = addinfourl(cStringIO('great'), 'OK', 'http://sentinel.uri')
    success.code = 200
    success.msg = 'OK'
    with patch(_open_director_open, return_value=success):
        with raises(IOError) as exc:
            pypirc.validate_credentials('http://sentinel.uri')
    assert repr(exc.value) == repr(IOError('Unexpected status from PyPi',
                                           'http://sentinel.uri', 200,
                                           'OK: great'))
