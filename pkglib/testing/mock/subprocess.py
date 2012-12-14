"""
        Subprocess Mock utilities.
"""
from importlib import import_module
from functools import wraps

# Slight hackery here: this is required to short-circuit the local package's namespace
subprocess = import_module('subprocess')

from mock import Mock, patch


#TODO: allow these to work as context managers

def get_subprocess_mock(stdout, stderr, returncode):
    """ Factory for a subprocess mock that returns the given results. 

        :param stdout:          Standard Output
        :param stderr:          Standard Error
        :param returncode:      Return Code
        :returns:               Mock object

        Eg::

            @patch_subprocess(get_subprocess_mock('foo','',0))
            def test_foo():
                .. test code goes here
                subprocess.Popen.assert_called_with('/bin/foo', shell=True, stderr=None, stdout=subprocess.PIPE)
    """
    res = Mock(spec=subprocess.Popen)
    res.communicate.return_value = (stdout, stderr)
    res.returncode = returncode
    return res


def patch_subprocess(target_mock):
    """ Decorator to patch subprocess with the given mock

        :param target_mock:     Mock used to specify return values

        Eg::

            @patch_subprocess(get_subprocess_mock('foo','',0))
            def test_foo():
                .. test code goes here
                subprocess.Popen.assert_called_with('/bin/foo', shell=True, stderr=None, stdout=subprocess.PIPE)
    """
    def wrapper(f):
        """ This is the equiv of::
                @patch(...)
                def f()
                    ...
        """
        # TODO: functools.wraps/update_wrapper or convert this decorator to an object
        return patch("subprocess.Popen", Mock(return_value=target_mock))(f)
    return wrapper
