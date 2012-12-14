"""Setuptools extensions"""
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
from command.pypirc import PyPIRCCommand
import distutils.config
distutils.config.PyPIRCCommand = PyPIRCCommand

__all__ = ['setup']

from ._setup import setup
