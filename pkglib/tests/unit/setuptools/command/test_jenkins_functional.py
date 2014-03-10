import imp
import pytest
import sys
import xml.etree.ElementTree

from contextlib import contextmanager

from mock import Mock, patch, ANY
from setuptools.dist import Distribution

import pkglib  # @UnusedImport

from six.moves import ExitStack  # @UnresolvedImport

from pkglib import config
from pkglib.setuptools.command import jenkins_

from .runner import patch_dict

from . import get_resource

with open(get_resource("jenkins_build_step.txt")) as f:
    COMMAND_TEMPLATE = f.read()


def xml_to_tree(xmlstr):
    return xml.etree.ElementTree.fromstring(xmlstr)


def create_oss_jenkins_mock_module(**kwargs):
    oss_jenkins = imp.new_module("foo")
    module_dict = {'PROD_JENKINS_SERVER': Mock()}
    module_dict.update(kwargs)
    if 'Jenkins' not in module_dict:
        jenkins_m = Mock(side_effect=lambda *_args, **_kwargs: jenkins_m)
        module_dict['Jenkins'] = jenkins_m
    oss_jenkins.__dict__.update(module_dict)
    return oss_jenkins


@contextmanager
def patch_oss_jenkins(**kwargs):
    jenkins_mock = create_oss_jenkins_mock_module(**kwargs)
    with patch_dict(sys.modules, {'jenkins': jenkins_mock}):
        yield


def get_cmd(**kwargs):
    metadata = {'name': 'acme.foo', 'version': '1.0.0'}
    metadata.update(kwargs)
    dist = Distribution(metadata)
    cmd = jenkins_.jenkins(dist)
    cmd.write_file = Mock()
    cmd.pin_requirements = Mock()
    cmd.run_command = Mock()
    cmd.fetch_build_eggs = Mock()
    return cmd


def job_description(job_xml):
    return job_xml.find('description').text


def job_display_name(job_xml):
    return job_xml.findtext('.//wallDisplayName')


def job_scm_location_remote(job_xml):
    tag = ".//hudson.scm.SubversionSCM_-ModuleLocation/remote"
    return job_xml.findtext(tag)


def job_scm_location_local(job_xml):
    tag = ".//hudson.scm.SubversionSCM_-ModuleLocation/local"
    return job_xml.findtext(tag)


def job_python_versions(job_xml):
    version_axis = job_xml.find('.//jenkins.plugins.shiningpanda.matrix.PythonAxis/values')
    assert all(el.tag == 'string' for el in version_axis)
    return [el.text for el in version_axis]


def job_build_steps(job_xml):
    return [s.text for s in job_xml.findall('.//command')]


def test_run__submits_matrix_job_with_correct_xml():
    project_name = "acme.foo"
    url = "http://some_fancytest_url"
    description = "This description is not very helpful\nBut OK for testing"
    username = "Churchill"
    env_python_versions = '2.6.2 1.2.3 1.9.8.4'
    TEST_CONFIG = config.OrganisationConfig(jenkins_matrix_job_pyversions=env_python_versions.split(),
                                            jenkins_url='http://acmejenkins.example.com',
                                            jenkins_matrix_job_xml=None,
                                            virtualenv_executable='virtualenv')

    expected_python_versions = ['2.6.2', '1.2.3', '1.9.8.4']
    expected_build_cmd = COMMAND_TEMPLATE % {'project_name': project_name,
                                             'egg_name': project_name}

    jenkins_mock = Mock(side_effect=lambda *_args, **_kwargs: jenkins_mock)
    jenkins_mock.job_exists = Mock(return_value=False)

    with ExitStack() as stack:
        stack.enter_context(patch.object(jenkins_, 'CONFIG', TEST_CONFIG))
        stack.enter_context(patch('getpass.getuser', return_value=username))
        stack.enter_context(patch('pkglib.setuptools.command.base.fetch_build_eggs'))
        stack.enter_context(patch_oss_jenkins(Jenkins=jenkins_mock))
        cmd = get_cmd(name=project_name, url=url, description=description)
        cmd.matrix = True
        cmd.run()

    job_xml = xml_to_tree(jenkins_mock.create_job.call_args[0][1])

    jenkins_mock.create_job.assert_called_once_with(project_name, ANY)
    assert job_description(job_xml) == description
    assert job_display_name(job_xml) == "%s (%s)" % (project_name, username)
    assert job_scm_location_remote(job_xml) == "%s/trunk" % url
    assert job_scm_location_local(job_xml) == project_name
    assert job_python_versions(job_xml) == expected_python_versions
    assert job_build_steps(job_xml)[2] == expected_build_cmd


def test__submits_matrix_job():
    project_name = "acme.foo.bar"
    url = "http://some_fancytest_url/" + project_name
    env_python_versions = '2.6.2 5.4.3 9.4.5.5'
    expected_python_versions = ['2.6.2', '5.4.3', '9.4.5.5']
    expected_build_cmd = COMMAND_TEMPLATE % {'project_name': project_name,
                                             'egg_name': project_name}
    TEST_CONFIG = config.OrganisationConfig(jenkins_matrix_job_pyversions=env_python_versions.split(),
                                            jenkins_url='http://acmejenkins.example.com',
                                            jenkins_matrix_job_xml=None,
                                            jenkins_job_xml=None,
                                            virtualenv_executable='virtualenv')

    jenkins_mock = Mock(side_effect=lambda *_args, **_kwargs: jenkins_mock)
    jenkins_mock.job_exists = Mock(return_value=False)

    with ExitStack() as stack:
        stack.enter_context(patch.object(jenkins_, 'CONFIG', TEST_CONFIG))
        stack.enter_context(patch('pkglib.setuptools.command.base.fetch_build_eggs'))
        stack.enter_context(patch_oss_jenkins(Jenkins=jenkins_mock))
        cmd = get_cmd(name=project_name, url=url, description='')
        cmd.matrix = True
        cmd.run()

    job_xml = xml_to_tree(jenkins_mock.create_job.call_args[0][1])

    jenkins_mock.create_job.assert_called_once_with(project_name, ANY)
    assert job_scm_location_remote(job_xml) == "%s/trunk" % url
    assert job_scm_location_local(job_xml) == project_name
    assert job_python_versions(job_xml) == expected_python_versions
    assert job_build_steps(job_xml)[2] == expected_build_cmd


@pytest.mark.parametrize("project_name", ["acme.foo-boo-bar",
                                          "acme.foo_boo-bar",
                                          "acme.foo-boo_bar",
                                          "acme.foo_boo_bar"])
def test__submits_core_job_hyphened_or_underscored_name(project_name):
    egg_name = project_name.replace('_', '?').replace('-', '?')
    url = "http://some_fancytest_url/" + project_name
    description = "This description is not very helpful\nFine for testing"
    username = "Lenin"
    expected_build_cmd = COMMAND_TEMPLATE % {'project_name': project_name,
                                             'egg_name': egg_name}

    jenkins_mock = Mock(side_effect=lambda *_args, **_kwargs: jenkins_mock)
    jenkins_mock.job_exists = Mock(return_value=False)

    TEST_CONFIG = config.OrganisationConfig(jenkins_url='http://acmejenkins.example.com',
                                            jenkins_matrix_job_xml=None,
                                            jenkins_matrix_job_pyversions=None,
                                            jenkins_job_xml=None,
                                            virtualenv_executable='virtualenv')

    with ExitStack() as stack:
        stack.enter_context(patch.object(jenkins_, 'CONFIG', TEST_CONFIG))
        stack.enter_context(patch('getpass.getuser', return_value=username))
        stack.enter_context(patch('pkglib.setuptools.command.base.fetch_build_eggs'))
        stack.enter_context(patch_oss_jenkins(Jenkins=jenkins_mock))
        cmd = get_cmd(name=project_name, url=url, description=description)
        cmd.run()

    job_xml = xml_to_tree(jenkins_mock.create_job.call_args[0][1])

    jenkins_mock.create_job.assert_called_once_with(project_name, ANY)
    assert job_description(job_xml) == description
    assert job_display_name(job_xml) == "%s (%s)" % (project_name, username)
    assert job_scm_location_remote(job_xml) == "%s/trunk" % url
    assert job_scm_location_local(job_xml) == project_name
    assert job_build_steps(job_xml)[2] == expected_build_cmd
