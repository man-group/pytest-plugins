""" General utility module for command-line and environment management
"""
import getpass
from contextlib import contextmanager

from six.moves import builtins, input as raw_input


@contextmanager
def patch_getpass(username, password):
    """
    Patches the getuser() and getpass() functions in the getpass module
    replacing them with user specified values.

    """
    getuser_prev_callable = getpass.getuser
    getpass_prev_callable = getpass.getpass

    def _getpass(prompt='Password: ', stream=None):  # @UnusedVariable
        """A monkey patch for getpass that returns a specified password."""
        return password

    try:
        getpass.getuser = lambda: username
        getpass.getpass = _getpass
        yield
    finally:
        getpass.getuser = getuser_prev_callable
        getpass.getpass = getpass_prev_callable


@contextmanager
def patch_raw_input(user_input):
    """
    Patches the raw_input() built in function returning specified user input.

    """
    _raw_input_func_name = raw_input.__name__  # @UndefinedVariable
    raw_input_prev_callable = getattr(builtins, _raw_input_func_name)

    def _raw_input(msg=None):  # @UnusedVariable
        return user_input

    try:
        setattr(builtins, _raw_input_func_name, _raw_input)
        yield
    finally:
        setattr(builtins, _raw_input_func_name, raw_input_prev_callable)