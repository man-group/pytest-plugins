import os
import sys

from mock import Mock, patch
from setuptools.dist import Distribution

from pkglib.setuptools.command import jenkins_
from pkglib import config


def get_cmd(**kwargs):
    metadata = {'name': 'acme.foo', 'version': '1.0.0'}
    metadata.update(kwargs)
    dist = Distribution(metadata)
    cmd = jenkins_.jenkins(dist)
    cmd.write_file = Mock()
    cmd.pin_requirements = Mock()
    cmd.run_command = Mock()
    jenkins_.fetch_build_eggs = Mock()
    return cmd


def test_get_active_python_versions__returns_system_python_by_default():
    cmd = get_cmd()
    with patch('pkglib.setuptools.command.jenkins_.CONFIG',
               config.OrganisationConfig(jenkins_matrix_job_pyversions=None)):
        actual = cmd._get_active_python_versions()
    expected = (".".join(str(s) for s in sys.version_info[0:3]),)
    assert list(actual) == list(expected)


def test_get_active_python_versions__with_config():
    cmd = get_cmd()
    with patch('pkglib.setuptools.command.jenkins_.CONFIG',
               config.OrganisationConfig(jenkins_matrix_job_pyversions=['1.2', '2.3'])):
        actual = cmd._get_active_python_versions()
    expected = ("1.2", "2.3")
    assert list(actual) == list(expected)


def test_construct_string_values__single_value():
    cmd = get_cmd()
    actual = cmd._construct_string_values((1,))
    expected = ("<string>1</string>")
    assert list(actual) == list(expected)


def test_construct_string_values__multiple_values():
    cmd = get_cmd()
    actual = cmd._construct_string_values((1, 2, 3))
    expected = ("<string>1</string>\n<string>2</string>\n<string>3</string>")
    assert list(actual) == list(expected)
