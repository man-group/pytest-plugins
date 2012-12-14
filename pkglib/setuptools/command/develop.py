import setuptools
from setuptools.command.develop import develop as _develop
from distutils import log

from base import CommandMixin


class develop(_develop, CommandMixin):
    """ Override base 'develop' command to pull in tests_require
        packages as well. While this does introduce a difference
        from the standard, everyone I've talked to finds the
        behaviour of dropping the test packages into the local
        directory irritating.

        There's a command-line option to re-enable the default behavior

        Also adds a command-line option to use only final (non-dev)
        versions of package dependencies, using zc.buildout's
        dependency resolution mechanisms

    """
    # TODO: trim this down of options that arent' used
    # Keeping this short list separate so I can look it up later.
    _user_options = [
        ('prefer-final', 'p', 'Will install final (non-dev) versions of dependencies'),
        ('no-test', 'T', 'Will not install testing dependencies'),
        ('no-build', None, 'Do not perform build'),
    ]
    user_options = _user_options + _develop.user_options
    boolean_options = _develop.boolean_options + [
        'prefer-final',
        'no-test',
        'no-build',
    ]

    def initialize_options(self):
        _develop.initialize_options(self)
        self.prefer_final = False
        self.no_test = False
        self.no_build = False

    def run(self):
        # Lazy imports here to allow pkgutils to bootstrap itself.
        from pkglib.setuptools.buildout import install

        # Add the test packages into the same pool of dependencies as the
        # install_requires. This will stop them being dropped into the
        # package root dir, which is both irritating and stops the tests
        # from working if you don't run them via setup.py
        install_requirements = self.distribution.install_requires[:]
        if not self.no_test:
            install_requirements += self.distribution.tests_require

        # Next two sections comes from regualar easy_install's develop command

        # First make sure the metadata is up-to-date
        self.run_command('egg_info')

        if not self.no_build:
            # Build extensions in-place
            self.reinitialize_command('build_ext', inplace=1)
            self.run_command('build_ext')

            self.install_site_py()  # ensure that target dir is site-safe
            if setuptools.bootstrap_install_from:
                self.easy_install(setuptools.bootstrap_install_from)
                setuptools.bootstrap_install_from = None

        # Now grab all the dependencies using buildout
        if not self.no_deps:
            # We're running now in 'buildout' mode, so by default we dont use dev versions
            # of any dependencies unless asked for.
            add_to_global = False
            force_upgrade = False

            # Here we set use_existing as the inverse of the command-line --prefer-final,
            # as we want the installer to get new version of things if they're available
            use_existing = not self.prefer_final

            ws = self.execute(install, (self, install_requirements, add_to_global,
                                        self.prefer_final, force_upgrade, use_existing),
                              msg="Installing dependencies")
            log.debug("Installed dependencies:")
            if ws:
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

        # Cleanup site-packages
        self.execute(self.run_cleanup_in_subprocess, (), "Cleaning up site-packages")
