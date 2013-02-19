#!/bin/env python
import sys
from distutils import log

try:
    from setuptools import _distribute
except ImportError, e:
    log.fatal("Please install distribute to continue. "
              "Eg: 'easy_install distribute'. \n"
              "If using virtualenv you can do this with "
              "'virtualenv pyenv --distribute'")
    sys.exit(1)

from setuptools.command import develop, easy_install
from setuptools.dist import Distribution

from pkglib import config, CONFIG
from pkglib.setuptools import _setup
from pkglib.setuptools.command import develop as pkglib_develop


def get_index_url():
    url = CONFIG.pypi_url
    if not url.endswith('/simple') and not url.endswith('/simple/'):
        url += '/simple'
    return url


class PkgLibBootStrapDistribution(Distribution):
    """ Used to enable our config system for pre-setup reqs.
    """
    def fetch_build_egg(self, req):
        try:
            cmd = self._egg_fetcher
        except AttributeError:
            dist = self.__class__({'script_args': ['easy_install']})
            dist.parse_config_files()
            cmd = easy_install.easy_install(dist, args=['x'],
                                            index_url=get_index_url())
            cmd.ensure_finalized()
            self._egg_fetcher = cmd
        return cmd.easy_install(req)


# These are the setup arguments used when bootstrapping pkglib
setup_args = dict(
    entry_points={
        'pytest11': ['pytest_profile = pkglib.testing.pytest.profile'],
        'paste.paster_create_template':
            ['pkglib_project = pkglib.project_template.paste_template:' \
                                'CorePackage']
    },
    extras_require={'dot': ['gprof2dot']},
    # We have to use vanilla develop command here, as we require 3rd party
    # libraries for our installer to work.
    cmdclass={'develop': develop.develop},
    distclass=PkgLibBootStrapDistribution,
)

if __name__ == '__main__':
    # This defaults to WARN, not so fun for debugging setup_requires
    log.set_threshold(log.INFO)

    if 'develop' in sys.argv and '--help' not in sys.argv \
        and '-h' not in sys.argv:
        # We have to use vanilla develop command here, as we require 3rd party
        # libraries for our installer to work.

        # First strip off any of our extra options as these will break vanilla
        # easy_install.
        for (l_arg, s_arg, desc) in pkglib_develop.develop._user_options:
            if '--%s' % l_arg in sys.argv:
                sys.argv.remove('--%s' % l_arg)
            if s_arg and '-%s' % s_arg in sys.argv:
                sys.argv.remove('-%s' % s_arg)

        # Read in our org config as to use a non-standard package index we'll
        # need to set vanilla develop's command-line manually
        config.setup_org_config()
        sys.argv.extend(['-i', get_index_url()])

    # Run setup with our boostrapping args
    _setup.setup(**setup_args)
