#
#   A monkey patch for the distutils.config.PyPIRCCommand.
#
#   Adds support for the prompting of PyPI login details with performing
#   any distutils/setuptools command which pushes data to the PyPI server.
#
#   It also prevents the saving of passwords to the .pypirc file in the
#   user's home directory and prompts of the password if it has been left
#   out of the configuration file.
#

# This line needs to be above anything imported from setuptools
import patches  # @UnusedImport # NOQA

import distutils.config
import distutils.core

from pkglib.setuptools.command.pypirc import PyPIRCCommand

distutils.config.PyPIRCCommand = PyPIRCCommand
distutils.core.PyPIRCCommand = PyPIRCCommand

from ._setup import setup
from .dist import Distribution


__all__ = ['setup', 'Distribution']
