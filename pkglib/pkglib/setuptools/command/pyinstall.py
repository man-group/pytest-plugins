import os

from setuptools import Command
from distutils.errors import DistutilsOptionError
from distutils import log

import pkg_resources

from pkglib import CONFIG
from pkglib.setuptools.dist import egg_distribution

from .base import CommandMixin, get_easy_install_cmd


def _extract_egg_args(args):
    eggs, reqs = [], []
    for arg in args:
        if os.path.exists(arg) and os.path.splitext(arg)[1] == '.egg':
            eggs.append(arg)
            reqs.append(str(egg_distribution(arg).as_requirement()))
        else:
            reqs.append(arg)
    return eggs, reqs


class pyinstall(Command, CommandMixin):
    """ Python Package installer.
    """
    description = '\n'.join(["Install and upgrade Python packages.",
                             ])

    command_consumes_arguments = True

    user_options = [
        ('dev', None, "Installs development packages if they are available"),
        ('update', 'U', "Forces an update of packages and their dependencies, "
         "respecting source checkouts."),
        ('third-party', 't', 'Update only: include third-party packages'),
        ("index-url=", "i", "base URL of Python Package Index"),
        ('source', 's', 'Update only: include only source checkouts'),
        ('eggs', 'e', 'Update only: include only eggs'),
        ('everything', 'E', 'Update only: include all currently installed '
         'packages'),
    ]
    boolean_options = [
        'dev',
        'update',
        'everything',
        'third_party',
        'source',
        'eggs',
    ]

    def initialize_options(self):
        self.args = []
        self.dev = False
        self.update = False
        self.everything = False
        self.third_party = False
        self.source = False
        self.eggs = False
        self.index_url = None

    def finalize_options(self):
        # UNKNOWN distro name is set when this is run from pyinstall the
        # command-line app.
        if self.distribution.get_name() == 'UNKNOWN' and not self.args:
            raise DistutilsOptionError("Please specify some packages "
                                       "requirements.")

        if not self.update:
            self.egg_args, self.args = _extract_egg_args(self.args)

        if self.dev and not self.update and not self.egg_args:
            # If we're not in update mode, figure out whether or not what
            # we've asked to install is already installed, and upgrade it
            # instead.
            # This switch only works if all of the requirements
            # are being upgraded at once.
            installed = [i.project_name in pkg_resources.working_set.by_key
                         for i in pkg_resources.parse_requirements(self.args)]
            if any(installed):
                # Some of our requirements are already installed. We swap to
                # update mode but only if they're all being update at once
                if not all(installed):
                    msg = ['Cannot run an install and update at the same time.',
                           'Please specify fewer requirements.',
                           ]
                    raise DistutilsOptionError('\n'.join(msg))
                log.info("Requirements already installed, performing an "
                         "update")
                self.update = True

        if self.update and not self.dev:
            # We need to check if we're trying to update to a released version
            # In this case we really should be doing an install instead as
            # upgrading will most likely cause dependency errors.
            log.info("Updating to a released version, performing an direct "
                     "install.")
            self.update = False
            self.egg_args = None

        self.index_url = self.maybe_add_simple_index(CONFIG.pypi_url)

    def run(self):
        # Lazy import here to allow pkgutils to bootstrap itself
        from pkglib.setuptools.buildout import install
        from zc.buildout.easy_install import MissingDistribution

        if self.update:
            # Update mode - call the pyupdate command
            cls = self.distribution.get_command_class('update')

            cmd = cls(self.distribution,
                      dev=self.dev,
                      everything=self.everything,
                      third_party=self.third_party,
                      source=self.source,
                      eggs=self.eggs,
                      index_url=self.index_url)

            cmd.args = self.args
            cmd.ensure_finalized()
            cmd.no_cleanup = True
            cmd.run()
        else:
            try:
                cmd = get_easy_install_cmd(self.distribution,
                                           index_url=self.index_url)
                install(cmd, self.args,
                        eggs=self.egg_args,
                        prefer_final=not self.dev,
                        force_upgrade=False,
                        reinstall=True)
            except MissingDistribution as e:
                raise DistutilsOptionError(str(e))

        self.execute(self.run_cleanup_in_subprocess, (),
                     'Cleaning up site-packages')
