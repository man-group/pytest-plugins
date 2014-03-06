from __future__ import absolute_import

from distutils import log

import pkg_resources
import setuptools

from setuptools.command.develop import develop as _develop

from .base import CommandMixin, merge_options
from .easy_install import easy_install


class develop(_develop, easy_install, CommandMixin):
    """ Override base 'develop' command to pull in tests_require
        packages as well. While this does introduce a difference
        from the standard, everyone I've talked to finds the
        behaviour of dropping the test packages into the local
        directory irritating.

        There's a command-line option to re-enable the default behaviour

        Also adds a command-line option to use only final (non-dev)
        versions of package dependencies, using zc.buildout's
        dependency resolution mechanisms

    """
    # TODO: trim this down of options that aren't used
    # Keeping this short list separate so I can look it up later.
    _pkglib_develop_user_options = [
        ('prefer-final', 'p',
         'Will install final (non-dev) versions of dependencies'),
        ('no-test', 'T', 'Will not install testing dependencies'),
        ('no-extras', None, 'Will not install extras'),
        ('no-build', None, 'Do not perform build')]
    user_options = merge_options(_develop.user_options,
                                 _pkglib_develop_user_options)

    _pkglib_develop_boolean_options = [
        'prefer-final',
        'no-test',
        'no-extras',
        'no-build']
    boolean_options = merge_options(_develop.boolean_options,
                                    _pkglib_develop_boolean_options)

    def initialize_options(self):
        _develop.initialize_options(self)
        easy_install.initialize_options(self)
        self.prefer_final = False
        self.no_test = False
        self.no_extras = False
        self.no_build = False
        self.index_url = self.maybe_add_simple_index(CONFIG.pypi_url)

    def finalize_options(self):
        _develop.finalize_options(self)
        easy_install.finalize_options(self)
        self.test = not self.no_test
        self.extras = not self.no_extras
        self.should_build = not self.no_build

    def run(self):

        # Next two sections comes from regular easy_install's develop command

        # First make sure the metadata is up-to-date
        self.run_command('egg_info')

        if self.should_build:
            # Build extensions in-place
            self.reinitialize_command('build_ext', inplace=1)
            self.run_command('build_ext')

            self.install_site_py()  # ensure that target dir is site-safe
            if setuptools.bootstrap_install_from:
                self.easy_install(setuptools.bootstrap_install_from)
                setuptools.bootstrap_install_from = None

        # Now grab all the dependencies using buildout
        if not self.no_deps:

            # Lazy imports here to allow ahl.pkgutils to bootstrap itself.
            from pkglib.setuptools.buildout import install

            # We're running now in 'buildout' mode, so by default we dont use
            # dev versions of any dependencies unless asked for.
            add_to_global = False
            force_upgrade = False

            # Here we set use_existing as the inverse of the command-line
            # `--prefer-final`, as we want the installer to get new version of
            # things if they're available
            use_existing = not self.prefer_final

            # To handle cyclic dependencies the distribution being setup must
            # be present in the working set before dependencies are processed
            pkg_resources.working_set.add(self.dist)

            # Add the test packages into the same pool of dependencies as the
            # install_requires. This will stop them being dropped into the
            # package root dir, which is both irritating and stops the tests
            # from working if you don't run them via setup.py
            install_reqs = list(self.get_requirements(extras=self.extras,
                                                      test=self.test))

            ws = self.execute(install, (self, install_reqs, add_to_global,
                                        self.prefer_final, force_upgrade,
                                        use_existing),
                              msg="Installing dependencies")
            if ws:
                log.debug("Installed dependencies:")
                for i in ws:
                    log.debug(i)

        # Then install the egg-link for this package
        log.info("Creating %s (link to %s)", self.egg_link, self.egg_base)
        if not self.dry_run:
            f = open(self.egg_link, "w")
            f.write(self.egg_path + "\n" + self.setup_path)
            f.close()

        # Do the rest of the develop setup, excluding the dependencies
        self.process_distribution(None, self.dist, deps=False)

        if not self.no_deps:  # Cleanup site-packages
            self.execute(self.run_cleanup_in_subprocess, (),
                         "Cleaning up site-packages")
