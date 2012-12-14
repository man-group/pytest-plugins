import contextlib
import ConfigParser

from setuptools.dist import Distribution

from mock import patch, Mock, MagicMock
import path

from pkglib import manage, config
from pkglib.setuptools.command import test_egg


CWD = Mock(spec=path.path.getcwd, return_value=path.path("/foo"))


def get_cmd():
    return test_egg.test_egg(Distribution({'name': 'acme.foo',
                                           'tests_require': ['bar', 'baz'],
                                           'namespace_packages': ['acme'],
                                           'packages': ['acme.foo']}))


def test_options():
    with patch.object(path.path, 'getcwd', CWD):
        cmd = get_cmd()
        cmd.finalize_options()

        assert cmd.test_dir == '/foo/tests'
        assert cmd.dest_dir == 'build/lib/acmetests/acme/foo'
        assert cmd.distribution.metadata.name == 'test.acme.foo'
        assert cmd.distribution.namespace_packages == ['acmetests', 'acmetests.acme']
        assert cmd.distribution.install_requires == ['bar', 'baz', 'acme.foo==0.0.0']


def test_get_file_dest():
    with patch.object(path.path, 'getcwd', CWD):
        cmd = get_cmd()
        cmd.finalize_options()
        assert cmd.get_file_dest('/foo/tests/integration/test_foo.py') == \
                'build/lib/acmetests/acme/foo/integration/test_foo.py'


def test_copy_file():
    with patch.object(path.path, 'getcwd', CWD):
        with patch.object(path.path, 'copyfile', Mock(spec=path.path.copyfile)) as copy_mock:
            dist = Distribution({'name': 'acme.foo'})
            cmd = test_egg.test_egg(dist)
            src = Mock()
            dest = Mock()

            cmd._copy_file(src, dest)

            dest.parent.makedirs_p.assert_called_once_with()
            copy_mock.assert_called_once_with(src, dest)


def _test_init_files(exists):
    with patch.object(path.path, 'getcwd', CWD):
        dist = Distribution({'name': 'acme.foo'})
        cmd = test_egg.test_egg(dist)

        top_dir = MagicMock()
        top_init_file = Mock()
        top_init_file.isfile.return_value = exists

        sub_init_file = Mock()
        sub_init_file.isfile.return_value = exists

        sub_dir = MagicMock()
        sub_dir.__div__.return_value = sub_init_file

        top_dir.walkdirs.return_value = [sub_dir, '.svn', '__pycache__']
        top_dir.__div__.return_value = top_init_file

        cmd.create_init_files(top_dir)
        return top_init_file, sub_init_file


def test_create_init_files():
    for init_file in _test_init_files(False):
        init_file.write_text.assert_called_once_with('')


def test_creating_init_files_already_exist():
    for init_file in _test_init_files(True):
        assert not init_file.write_text.call_args_list


def test_create_pytest_config():
    parser = ConfigParser.ConfigParser()
    parser.add_section('foo')
    parser.add_section('bar')
    parser.add_section('pytest')
    parser.write = Mock()
    filename = Mock()
    fp = MagicMock()
    filename.open.return_value = fp

    with patch.object(config, 'get_pkg_cfg_parser', Mock(return_value=parser)):
        cmd = get_cmd()
        cmd.create_pytest_config(filename)
        assert parser.sections() == ['pytest']


def test_ns_pkg_files():
    with patch.object(path.path, 'getcwd', CWD):
        with patch.object(path.path, 'write_text') as mock_write:
            cmd = get_cmd()
            cmd.finalize_options()

            top_dir = path.path('build/lib')
            top_dir.isdir = lambda: True

            sub_dir1 = path.path('build/lib/acmetests')
            sub_dir2 = path.path('build/lib/acmetests/acme')
            sub_dir3 = path.path('build/lib/acmetests/acme/foo')

            top_dir.walkdirs = lambda: [sub_dir1, sub_dir2, sub_dir3]

            cmd.create_ns_pkg_files(top_dir)

            assert mock_write.call_args_list == [
                 ((test_egg.NAMESPACE_PACKAGE_INIT,), {}),
                 ((test_egg.NAMESPACE_PACKAGE_INIT,), {})]


def test_run():
    with contextlib.nested(patch.object(path.path, 'getcwd', CWD),
                           patch.object(test_egg._bdist_egg, 'run'),
                           patch.object(test_egg, 'find_packages',
                                        Mock(return_value=['integration', 'unit']))):
        cmd = get_cmd()
        cmd.finalize_options()

        test_dir = Mock()
        test_dir.isdir.return_value = True
        cmd.test_dir = test_dir

        cmd._copy_file = Mock()
        cmd.get_file_dest = Mock(return_value='dest')
        cmd.create_init_files = Mock()
        cmd.create_pytest_config = Mock()
        cmd.get_finalized_command = Mock()
        cmd.dest_dir = MagicMock()
        cmd.dest_dir.__div__.return_value = '/xxx/pytest.ini'
        cmd.egg_info = Mock()

        class MyFile(str):
            def isfile(self):
                return True
        files = [MyFile(i) for i in ['.svn', '__pycache__', 'foo', 'bar', 'baz']]
        test_dir.walk.return_value = files

        cmd.run()

        assert cmd._copy_file.call_args_list == \
            [(('foo', 'dest'), {}), (('bar', 'dest'), {}), (('baz', 'dest'), {})]

        cmd.create_init_files.assert_called_once_with(test_dir)
        cmd.create_pytest_config.assert_called_once_with('/xxx/pytest.ini')

        assert cmd.distribution.packages == ['acmetests.acme.foo.integration',
                                             'acmetests.acme.foo.unit']
