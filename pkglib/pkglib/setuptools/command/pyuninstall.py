from collections import namedtuple
import distutils

from setuptools import Command
from pip.commands import uninstall
from pip.log import logger
from pip import exceptions

from base import CommandMixin

class pyuninstall(Command, CommandMixin):
    """ Remove a package. Calls pip.uninstall """
    description = "Remove a package. Uses pip.uninstall"
    command_consumes_arguments = True

    user_options = [
        ('yes', 'y', "Don't ask for confirmation of uninstall deletions."),
    ]
    boolean_options = [
        'yes',
    ]

    def initialize_options(self):
        self.yes = False
        self.args = []

    def finalize_options(self):
        pass

    def run(self):
        """ Wire in the pip uninstall command
        """
        # Pip has some non-standard log levels, we'll wire them back into regular logging
        # or they get hidden from the user
        logger.notify = distutils.log.info
        logger.debug = distutils.log.debug
        logger.info = distutils.log.info
        logger.error = distutils.log.error
        logger.fatal = distutils.log.fatal
        logger.warn = distutils.log.warn

        # Pip uses OptionsParser objects, which we mock up here.
        options = namedtuple('options', ['yes', 'requirements'])
        setattr(options, 'yes', self.yes)
        setattr(options, 'requirements', [])
        try:
            uninstall.UninstallCommand().run(options, self.args)
        except exceptions.UninstallationError, e:
            distutils.log.fatal(e)
