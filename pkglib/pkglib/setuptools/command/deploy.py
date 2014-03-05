from setuptools import Command
from distutils.errors import DistutilsOptionError

from pkglib import manage, errors

from base import CommandMixin


class deploy(Command, CommandMixin):
    """ Install this package under ``config.deploy_path``
    """
    description = "Install this under ``config.deploy_path`` (disabled by default)."

    user_options = [
        ('enabled', None, 'Enable this command.'),
        ("index-url=", "i", "base URL of Python Package Index"),
    ]

    boolean_options = [
        'enabled',
    ]

    def initialize_options(self):
        self.enabled = False
        self.egg_file = None

    def finalize_options(self):
        pass

    def run(self):
        if not self.enabled:
            return

        if not self.egg_file:
            # pre-requisite is an egg file to install.
            self.run_command('bdist_egg')
            cmd = self.distribution.get_command_obj('bdist_egg')
            self.egg_file = cmd.egg_output

        try:
            manage.deploy_pkg(self.egg_file, pypi_index_url=self.index_url)

        except errors.UserError as ex:
            raise DistutilsOptionError(ex.msg)
