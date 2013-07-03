import os
from setuptools import Command
from distutils.errors import DistutilsOptionError
from distutils import log

from pkg_resources import resource_filename

from pkglib.cmdline import run
from pkglib import manage, CONFIG

from base import CommandMixin


class deploy(Command, CommandMixin):
    """ Install this package under ``config.deploy_path``
    """
    description = "Install this under ``config.deploy_path`` (disabled by default)."

    user_options = [
        ('enabled', None, 'Enable this command.'),
        ('console-scripts', None, 'Console scripts to symlink under ``config.deploy_bin``'),
    ]

    boolean_options = [
        'enabled',
    ]

    def initialize_options(self):
        self.enabled = False
        self.console_scripts = []

    def finalize_options(self):
        if self.console_scripts:
            self.console_scripts = self.parse_multiline(self.console_scripts)

    def run(self):
        if not self.enabled:
            return

        from path import path

        # Pre-requisite is an egg file to install.
        self.run_command('bdist_egg')

        version = self.distribution.metadata.get_version()
        package_dir = path(CONFIG.deploy_path) / self.distribution.metadata.get_name()
        pyenv_dir = package_dir / version

        # Set umask for file creation: 0022 which is 'rwx r.x r.x'
        os.umask(0022)

        if pyenv_dir.isdir():
            raise DistutilsOptionError("Package already installed at %s" % pyenv_dir)

        self.execute(manage.create_virtualenv, (pyenv_dir,),
                     "creating virtualenv at %s" % pyenv_dir)
        self.execute(manage.install_pkg, (pyenv_dir, 'pkglib'),
                     "installing pkglib into virtualenv at %s" % pyenv_dir)

        # Install the built egg
        egg_file = self.distribution.get_command_obj('bdist_egg').egg_output

        # TODO: make pyisntall work with egg files, or fix setup.py install so we can
        #       make use of the egg cache

        # Running easy_install as a script here to get around any #! length limits
        self.execute(run, ((pyenv_dir / 'bin' / 'python',
                           pyenv_dir / 'bin' / 'easy_install', egg_file),),

                     "installing this package into virtualenv at %s" % pyenv_dir)
        current_link = package_dir / 'current'
        if current_link.islink():
            self.execute(current_link.unlink, (), "removing current link %s" % current_link)
        self.execute(self.create_relative_link, (current_link, version),
                     "creating current link %s -> %s" % (current_link, version))

        for item in self.console_scripts:
            src = path(CONFIG.deploy_bin) / item
            dest = current_link / 'bin' / item
            if src.islink():
                self.execute(src.unlink, (), "Removing console script link %s" % src)
            self.execute(self.create_relative_link, (src, dest),
                         "linking console script %s -> %s" % (src, dest))
