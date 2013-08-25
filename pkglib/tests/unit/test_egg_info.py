from setuptools.dist import Distribution
from mock import Mock, patch
import pytest

from pkglib.setuptools.command import egg_info
from pkglib.pypi.xmlrpc import XMLRPCPyPIAPI

from helper import Pkg


def get_cmd(version='1.0.0'):
    dist = Distribution({'name': 'acme.foo', 'version': version})
    cmd = egg_info.egg_info(dist)
    cmd.write_file = Mock()
    cmd.pin_requirements = Mock()
    return cmd


def test_finalize_options():
    cmd = get_cmd()
    cmd.finalize_options()
    assert cmd.revision_file == "%s/revision.txt" % cmd.egg_info


def test_write_revision():
    cmd = get_cmd()
    cmd.finalize_options()
    cmd.write_revision('12345')
    args, kwargs = cmd.write_file.call_args_list[0]
    assert args[1] == cmd.revision_file
    assert args[2] == '12345'


def test_write_options():
    cmd = get_cmd()
    cmd.finalize_options()
    test_cmd = Mock()
    cmd.get_finalized_command = Mock(return_value=test_cmd)
    test_cmd.get_options.return_value = [('foo', 'bar'), ('baz', 'qux')]

    cmd.write_test_options()
    args, kwargs = cmd.write_file.call_args_list[0]
    assert args[1] == cmd.test_option_file
    assert args[2] == "[test]\nfoo = bar\nbaz = qux"


def test_get_new_build_number_not_dev_version():
    with patch('pkglib.pypi.xmlrpc.XMLRPCPyPIAPI.get_last_version',
               Mock(return_value='1.0.0')):
        cmd = get_cmd('1.0.0')
        cmd.pypi_client = XMLRPCPyPIAPI('http://example.com')
        cmd.new_build = True
        with pytest.raises(ValueError):
            cmd.finalize_options()


def test_get_new_build_number_old_style_dev_version():
    with patch('pkglib.pypi.xmlrpc.XMLRPCPyPIAPI.get_last_version',
               Mock(return_value='1.0.0.dev2')):
        cmd = get_cmd('1.0.0')
        cmd.pypi_client = XMLRPCPyPIAPI('http://example.com')
        cmd.new_build = True
        with pytest.raises(ValueError):
            cmd.finalize_options()


def test_get_new_build_number_no_dev_versions_yet():
    with patch('pkglib.pypi.xmlrpc.XMLRPCPyPIAPI.get_last_version',
               Mock(return_value=None)):
        cmd = get_cmd('1.0.0')
        cmd.pypi_client = XMLRPCPyPIAPI('http://example.com')
        cmd.new_build = True
        cmd.finalize_options()
        assert cmd.egg_version == '0.0.dev1'


def test_get_new_build_number():
    with patch('pkglib.pypi.xmlrpc.XMLRPCPyPIAPI.get_last_version',
               Mock(return_value='0.0.dev2')):
        cmd = get_cmd('1.0.0')
        cmd.pypi_client = XMLRPCPyPIAPI('http://example.com')
        cmd.new_build = True
        cmd.finalize_options()
        assert cmd.egg_version == '0.0.dev3'


def test_pin_requirements_not_installed():
    dist = Distribution({'name': 'acme.foo', 'version':'1.0.0',
                         'install_requires': ['foo', 'bar']})
    cmd = egg_info.egg_info(dist)
    with patch('pkg_resources.working_set', []):
        with pytest.raises(ValueError):
            cmd.pin_requirements()


def test_pin_requirements():
    dist = Distribution({'name': 'acme.foo', 'version':'1.0.0',
                         'install_requires': ['foo', 'bar'],
                         'tests_require': ['baz']})
    cmd = egg_info.egg_info(dist)
    my_working_set = [
       Pkg('foo', [], version='2.2.2'),
       Pkg('bar', [], version='3.3.3'),
       Pkg('baz', [], version='4.4.4'),
    ]

    with patch('pkg_resources.working_set', my_working_set):
        cmd.pin_requirements()
        assert cmd.distribution.install_requires == ['foo==2.2.2', 'bar==3.3.3']
        assert cmd.distribution.tests_require == ['baz==4.4.4']

