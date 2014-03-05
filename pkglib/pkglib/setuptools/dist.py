# Monkey-patch fixes for distutils.Distribution:

import os
import shutil
import tempfile
import logging
from contextlib import contextmanager
import zipimport

from pkg_resources import EggMetadata, PathMetadata
from setuptools.dist import Distribution as _Distribution

import pkg_resources

from .command.base import fetch_build_eggs


CFG_VAR = "DISTUTILS_CONFIG_FILE"


class Distribution(_Distribution):

    def __init__(self, attrs=None):
        self.attrs = dict(attrs or {})
        self.original_cwd = self.attrs.get('original_cwd', os.getcwd())
        self.fetched_setup_requires = []
        self.trace_ws = False

        # Track all `setup_requires` dependencies which are fetched
        def ws_callback(dist):
            if self.trace_ws:
                self.fetched_setup_requires.append(dist)

        pkg_resources.working_set.subscribe(ws_callback)
        self.trace_ws = True
        _Distribution.__init__(self, attrs=attrs)
        self.trace_ws = False

    def run_commands(self):
        logging.basicConfig()
        level = ['WARN', 'INFO', 'DEBUG'][max(0, min(self.verbose, 2))]
        logging.root.setLevel(level)
        _Distribution.run_commands(self)

    # https://bitbucket.org/tarek/distribute/issue/227/easy_install-doesnt-pass-its-arguments    # NOQA
    if not hasattr(_Distribution, '_fix_issue_227_parse_fetcher_opts'):

        if not hasattr(_Distribution, "_set_fetcher_options"):
            def _set_fetcher_options(self, base):
                """
                When easy_install is about to run bdist_egg on a source dist,
                that source dist might have 'setup_requires' directives,
                requiring additional fetching. Ensure the fetcher options given
                to easy_install are available to that command as well.
                """
                from setuptools.command import setopt
                # find the fetch options from easy_install and write them out
                #  to the setup.cfg file.
                ei_opts = self.distribution.get_option_dict('easy_install'
                                                            ).copy()
                fetch_directives = (
                    'find_links', 'site_dirs', 'index_url', 'optimize',
                    'site_dirs', 'allow_hosts',
                )
                fetch_options = {}
                for key, val in ei_opts.items():
                    if key not in fetch_directives:
                        continue
                    fetch_options[key.replace('_', '-')] = val[1]
                # create a settings dictionary suitable for `edit_config`
                settings = dict(easy_install=fetch_options)
                cfg_filename = os.path.join(base, 'setup.cfg')
                setopt.edit_config(cfg_filename, settings)

        def _fix_issue_227_parse_fetcher_opts(self):
            """
            When easy_install is about to run bdist_egg on a source dist, that
            source dist might have 'setup_requires' directives, requiring
            additional fetching. Ensure the fetcher options given to
            easy_install are available to that command as well.
            """
            # FIXME: the below is quite ugly and does not cover all of the
            # easy_install parameters, needs to be re-factored

            easy_install_opts = {}
            if not self.attrs or 'script_args' not in self.attrs:
                return easy_install_opts

            script_args = self.attrs['script_args']
            supported_opts = (("index_url", "--index-url", "-i"),)
            i = 0
            while i < len(script_args):
                for opt in supported_opts:
                    if script_args[i] == opt[1] or script_args[i] == opt[2]:
                        if i == len(script_args) - 1:
                            raise RuntimeError("Please provide " + opt[0])
                        easy_install_opts[opt[0]] = script_args[i + 1]
                        i = i + 1
                        break
                    elif script_args[i].startswith('%s=' % opt[1]):
                        arr = script_args[i].split('%s=' % opt[1])
                        if len(arr) == 1:
                            raise RuntimeError("Please provide %s " + opt[0])
                        easy_install_opts[opt[0]] = arr[1]
                        i = i + 1
                        break
                i = i + 1

            return dict((k, ['', v]) for k, v in easy_install_opts.items())

        def find_config_files(self):
            filenames = _Distribution.find_config_files(self)

            env_config_file = os.environ.get(CFG_VAR)

            if (env_config_file is not None and not
                any(os.path.realpath(f) == os.path.realpath(env_config_file)
                    for f in filenames)):
                filenames.append(env_config_file)

            return filenames

        @contextmanager
        def _patch_fetch_build_eggs(self, easy_install_opts):
            if not easy_install_opts:
                yield None
                return

            tmpdir = tempfile.mkdtemp()
            del_distribution = False
            del_command_options = False
            try:
                if not hasattr(self, 'distribution'):  # fake Distribution
                    del_distribution = True
                    from collections import namedtuple
                    d = namedtuple('Distribution', ['command_options',
                                                    'get_option_dict'])
                    self.distribution = d({}, lambda v:
                                          self.distribution.command_options[v])
                if not hasattr(self.distribution, 'command_options'):
                    del_command_options = True
                    self.distribution.command_options = {}
                self.distribution.command_options['easy_install'
                                                  ] = easy_install_opts
                self._set_fetcher_options(tmpdir)
                os.environ[CFG_VAR] = os.path.join(tmpdir, "setup.cfg")
                yield None
            finally:
                if del_distribution:
                    del self.distribution
                if del_command_options:
                    del self.distribution.command_options
                try:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                except:
                    pass

        def fetch_build_eggs(self, requires):
            if not requires:
                return

            easy_install_opts = self._fix_issue_227_parse_fetcher_opts()
            with self._patch_fetch_build_eggs(easy_install_opts):
                fetch_build_eggs(requires, dist=self)


def egg_distribution(egg_path):
    # from setuptools.command.easy_install.easy_install.egg_distribution -
    # it's an instance method even though it doesn't need to be
    if os.path.isdir(egg_path):
        metadata = PathMetadata(egg_path, os.path.join(egg_path, 'EGG-INFO'))
    else:
        metadata = EggMetadata(zipimport.zipimporter(egg_path))
    return Distribution.from_filename(egg_path, metadata=metadata)
