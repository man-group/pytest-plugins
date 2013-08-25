"""Setuptools extensions"""

# TODO: Why to we have to re-run this monkey-patch here?
from command.pypirc import PyPIRCCommand
import distutils.config
distutils.config.PyPIRCCommand = PyPIRCCommand

__all__ = ['setup']

from ._setup import setup
