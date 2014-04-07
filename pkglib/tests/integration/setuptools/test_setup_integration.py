from __future__ import print_function
import sys
import os
import subprocess
from collections import namedtuple
from mock import patch, Mock
from setuptools.dist import Distribution
import pytest
from pkglib_util.six.moves import configparser, cStringIO  # @UnresolvedImport
ConfigParser = configparser.ConfigParser

from pkglib.setuptools import setup as pkgutils_setup
from pkglib.setuptools.command.develop import develop as _develop
from pkglib_testing.util import PkgTemplate

from pkglib_util.six.moves import ExitStack

HERE = os.getcwd()


def test_setup_detects_double_call(pytestconfig):
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        setup_py = '%s/setup.py' % pkg.trunk_dir
        with open(setup_py, 'w') as f:
            f.write("""from pkglib.setuptools import setup
setup()
setup()
""")
        with pytest.raises(subprocess.CalledProcessError) as exc:
            print(pkg.run_with_coverage([setup_py, '--name'], pytestconfig,
                                        cd=HERE, capture_stderr=True))
        assert ('setup() has already been run! setup.py should only call'
                ' setup() once.') in exc.value.output


def _create_config_parser(content):

    class ConfigParserWithContent(ConfigParser):

        def read(self, filenames):
            if filenames == "setup.cfg":
                ConfigParser.readfp(self, cStringIO(content))
            else:
                ConfigParser.read(self, filenames)

    return ConfigParserWithContent


# XXX: tests original setuptools logic (i.e. bootstrapping mode)
def test_parse_setup_requires_fetcher_uses_index_url_from_command_line():
    setup_cfg = """
[metadata]
name = test3
setup_requires =
    foo
"""

    index_url = "http://my_super_duper_index/simplesteversimple"
    t = namedtuple("Distribution", ['requires', 'insert_on', 'location'])
    dist = t(lambda *_1, **_2: [], lambda *_1, **_2: None, "")

    def easy_install(self, *args, **kwargs):  # @UnusedVariable
        assert self.index_url == index_url
        return dist

    add_mock = Mock()

    class AssertCmd(_develop):
        def run(self):
            assert self.index_url == index_url

    with ExitStack() as stack:
        p = stack.enter_context
        p(patch("pkglib.setuptools._setup.set_working_dir"))
        p(patch(configparser.__name__ + ".ConfigParser",
                _create_config_parser(setup_cfg)))
        p(patch('setuptools.command.easy_install.easy_install.check_site_dir'))
        p(patch("setuptools.command.easy_install.easy_install.easy_install",
                new=easy_install))
        p(patch("pkg_resources.WorkingSet.add", new=add_mock))
        p(patch("pkglib.setuptools.dist.fetch_build_eggs", new=lambda r,
                dist=None: Distribution.fetch_build_eggs(dist, r)))
        sys.argv[1:] = ['develop', '-i', index_url]
        pkgutils_setup(cmdclass={'develop': AssertCmd})

        add_mock.assert_called_with(dist)
