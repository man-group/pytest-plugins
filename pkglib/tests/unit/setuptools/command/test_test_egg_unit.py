import os
from contextlib import contextmanager

from setuptools.dist import Distribution
from mock import patch, Mock

import pkglib  # @UnusedImport

from six.moves import configparser, ExitStack

from pkglib import config
from pkglib.setuptools.command import test_egg
from pkglib.setuptools.command.test_egg import NAMESPACE_PACKAGE_INIT

from .runner import _patch_open, patch_obj


CWD = Mock(return_value="/foo")


@contextmanager
def patched_cwd():
    with patch("os.getcwd", new=CWD):
        yield


def get_cmd():
    return test_egg.test_egg(Distribution({'name': 'acme.foo',
                                           'tests_require': ['bar', 'baz'],
                                           'namespace_packages': ['acme'],
                                           'packages': ['acme.foo']}))


def test_options():
    with patched_cwd():
        cmd = get_cmd()
        cmd.finalize_options()

        assert cmd.test_dir == '/foo/tests'
        assert cmd.dest_dir == 'build/lib/acmetests/acme/foo'
        assert cmd.distribution.metadata.name == 'test.acme.foo'
        assert cmd.distribution.namespace_packages == ['acmetests',
                                                       'acmetests.acme']
        assert cmd.distribution.install_requires == ['bar', 'baz',
                                                     'acme.foo==0.0.0']


def test_get_file_dest():
    with patched_cwd():
        cmd = get_cmd()
        cmd.finalize_options()

        file_dest = '/foo/tests/integration/test_foo.py'

        actual = cmd.get_file_dest(file_dest)

        assert actual == 'build/lib/acmetests/acme/foo/integration/test_foo.py'


def test_copy_file():
    with ExitStack() as stack:
        stack.enter_context(patched_cwd())
        makedirs_mock = stack.enter_context(patch("os.makedirs"))
        stack.enter_context(patch("os.path.exists", return_value=False))
        copy_mock = stack.enter_context(patch("shutil.copyfile"))

        dist = Distribution({'name': 'acme.foo'})
        cmd = test_egg.test_egg(dist)
        src = "<src>"
        dest = "<dest>"

        cmd._copy_file(src, dest)

        makedirs_mock.assert_called_once_with(CWD.return_value)
        copy_mock.assert_called_once_with(src, dest)


def _test_init_files(exists):
    with patched_cwd():
        dist = Distribution({'name': 'acme.foo'})
        cmd = test_egg.test_egg(dist)

        top_dirs = ['sub', '.svn', '__pycache__']
        walk_dirs = [("top", top_dirs, []), ("sub", [], [])]
        os_walk_mock = Mock(return_value=walk_dirs)

        with ExitStack() as stack:
            stack.enter_context(patch("os.path.isdir", return_value=True))
            stack.enter_context(patch("os.walk", new=os_walk_mock))
            stack.enter_context(patch("os.path.isfile", return_value=exists))
            files_written = stack.enter_context(_patch_open())

            cmd.create_init_files("top")

        assert top_dirs == ["sub"]

        return files_written


def test_create_init_files():
    files_written = _test_init_files(False)

    assert len(files_written) == 2
    for name, content in files_written.items():
        assert os.path.basename(name) == "__init__.py"
        assert content.string_value == ""


def test_creating_init_files_already_exist():
    assert len(_test_init_files(True)) == 0


def test_create_pytest_config():
    parser = configparser.ConfigParser()
    parser.add_section('foo')
    parser.add_section('bar')
    parser.add_section('pytest')
    parser.write = Mock()

    parser_mock = Mock(return_value=parser)

    with ExitStack() as stack:
        stack.enter_context(patch_obj(config, 'get_pkg_cfg_parser', parser_mock))
        stack.enter_context(_patch_open())

        cmd = get_cmd()
        cmd.create_pytest_config("<test>")
        assert parser.sections() == ['pytest']


def test_ns_pkg_files():
    with patched_cwd():
        cmd = get_cmd()
        cmd.finalize_options()

        top_dir = 'build/lib'

        dirs = [top_dir,
                'build/lib/acmetests',
                'build/lib/acmetests/acme',
                'build/lib/acmetests/acme/foo']

        with ExitStack() as stack:
            stack.enter_context(patch("os.path.isdir",
                                      side_effect=lambda f: f in dirs))
            stack.enter_context(patch("os.path.isfile", return_value=False))
            files_written = stack.enter_context(_patch_open())

            cmd.create_ns_pkg_files(top_dir)

        filenames = sorted(files_written.keys())
        assert filenames == ['build/lib/acmetests/__init__.py',
                             'build/lib/acmetests/acme/__init__.py']
        for content in files_written.values():
            assert content.string_value == NAMESPACE_PACKAGE_INIT


def test_run():
    with ExitStack() as stack:
        stack.enter_context(patched_cwd())
        stack.enter_context(patch_obj(test_egg._bdist_egg, 'run'))
        stack.enter_context(patch_obj(test_egg, 'find_packages',
                                      Mock(return_value=['integration',
                                                         'unit'])))

        cmd = get_cmd()
        cmd.finalize_options()

        cmd.test_dir = "/<test_dir>"
        cmd.dest_dir = "/xxx"

        cmd._copy_file = Mock()
        cmd.get_file_dest = Mock(return_value='dest')
        cmd.create_init_files = Mock()
        cmd.create_pytest_config = Mock()
        cmd.get_finalized_command = Mock()
        cmd.egg_info = Mock()

        walk_dirs = [("", ['.svn', '__pycache__'], ['foo', 'bar', 'baz'])]
        os_walk_mock = Mock(return_value=walk_dirs)

        with ExitStack() as stack:
            stack.enter_context(patch("os.path.isdir", return_value=True))
            stack.enter_context(patch("os.walk", new=os_walk_mock))
            stack.enter_context(patch("os.path.isfile", return_value=True))
            stack.enter_context(patch("shutil.rmtree"))
            stack.enter_context(_patch_open())

            cmd.run()

        expected_calls = [(('foo', 'dest'), {}),
                          (('bar', 'dest'), {}),
                          (('baz', 'dest'), {})]

        assert cmd._copy_file.call_args_list == expected_calls

        cmd.create_init_files.assert_called_once_with(cmd.test_dir)
        cmd.create_pytest_config.assert_called_once_with('/xxx/pytest.ini')

        assert cmd.distribution.packages == ['acmetests.acme.foo.integration',
                                             'acmetests.acme.foo.unit']
