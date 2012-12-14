from setuptools import Command
from distutils.errors import DistutilsOptionError
from distutils import log
import pkg_resources

from base import CommandMixin


class pyinstall(Command, CommandMixin):
    """ Python Package installer.
    """
    description = '\n'.join([
        "Install and upgrade Python packages.",
        ])

    command_consumes_arguments = True

    user_options = [
        ('dev', None, "Installs development packages if they are available"),
        ('update', 'U', "Forces an update of packages and their dependencies, respecting source checkouts."),
        ('third-party', 't', 'Update only: include third-party packages'),
        ("index-url=", "i", "base URL of Python Package Index"),
        ('source', 's', 'Update only: include only source checkouts'),
        ('eggs', 'e', 'Update only: include only eggs'),
        ('everything', 'E', 'Update only: include all currently installed packages'),
    ]
    boolean_options = [
        'dev',
        'update',
        'everything',
        'third_party',
        'source',
        'eggs',
        'artifact',
    ]

    def initialize_options(self):
        self.args = []
        self.dev = False
        self.update = False
        self.everything = False
        self.third_party = False
        self.both = True
        self.source = False
        self.eggs = False
        self.artifact = False
        self.from_artifact_dir = ''
        self.index_url = None

    def finalize_options(self):
        if self.artifact or self.from_artifact_dir:
            return

        if not self.update:
            # UNKNOWN distro name is set when this is run from pyinstall the command-line app.
            if self.distribution.get_name() == 'UNKNOWN' and not self.args:
                raise DistutilsOptionError('Please specify some packages requirements.')

        if not self.update:
            # If we're not in update mode, figure out whether or not what we've asked to
            # install is already installed, and upgrade it instead - but only if it's a
            # dev package.
            # This switch only works if all of the requirements
            # are being upgraded at once.

            reqs = list(pkg_resources.parse_requirements(self.args))
            req_names = [i.project_name for i in reqs]
            installed_req_dists = [i for i in pkg_resources.working_set if i.project_name in req_names]

            if installed_req_dists:
                # Some of our requirements are already installed. We swap to update mode
                # but only if they're all being update at once
                if len(reqs) != len(installed_req_dists):
                    raise DistutilsOptionError('\n'.join([
                        'Cannot run an install and update at the same time.',
                        'Please specify less requirements.',
                        ]))
                log.info("Requirements already installed, performing an update")
                self.update = True

        if self.update and not self.dev:
            # We need to check if we're trying to update to a released version
            # In this case we really should be doing an install instead as upgrading
            # will most likely cause dependency errors.
            log.info("Updating to a released version, performing an direct install.")
            self.update = False

    def run(self):
        # Lazy import here to allow pkgutils to bootstrap itself
        from pkglib.setuptools.buildout import install

        if not self.update:
            install(self.get_easy_install_cmd(index_url=self.index_url), self.args, prefer_final=not self.dev,
                    force_upgrade=self.update)
        else:
            # Update mode - call the pyupdate command
            cls = self.distribution.get_command_class('update')
            cmd = cls(self.distribution, dev=self.dev, everything=self.everything,
                      third_party=self.third_party, source=self.source, eggs=self.eggs,
                      index_url=self.index_url)
            cmd.args = self.args
            cmd.ensure_finalized()
            cmd.no_cleanup = True
            cmd.run()

        self.execute(self.run_cleanup_in_subprocess, (), 'Cleaning up site-packages')
