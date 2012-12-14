#!/bin/env python
import sys

from pkglib.setuptools import _setup
from setuptools.command import develop
from pkglib.setuptools.command import develop as pkglib_develop


setup_args = dict(
    entry_points={'pytest11': ['pytest_profile = pkglib.testing.pytest.profile']},
    extras_require={'dot': ['gprof2dot']},
    cmdclass={'develop': develop.develop},
)

# Handle bootstrapping development: we have to skip the tests_include
# for setup.py develop as I've not managed to find a way to get those
# packages to find pkglib as its being installed, not matter
# how hard I try - its like until this process exits, the egg-link
# isn't valid or somesuch.

if 'develop' in sys.argv and '--help' not in sys.argv and '-h' not in sys.argv:
    # We have to use vanilla develop command here, as we require 3rd party things for the installer
    # First strip off any of our extra options as these will break vanilla easy_install
    for (l_arg, s_arg, desc) in pkglib_develop.develop._user_options:
        if '--%s' % l_arg in sys.argv:
            sys.argv.remove('--%s' % l_arg)
        if s_arg and '-%s' % s_arg in sys.argv:
            sys.argv.remove('-%s' % s_arg)
    # Now override the develop cmdclass back to the original
    _setup.setup(tests_require=[], **setup_args)
else:
    _setup.setup(**setup_args)
