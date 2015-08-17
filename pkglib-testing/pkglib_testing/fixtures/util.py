"""     Pytest general util stuff.
"""
import functools

import pytest

from pkglib_testing import CONFIG


# Note this is now supported natively in py.test using the following decorator
# @pytest.mark.parametrize(("input", "expected"), [
#    ("3+5", 8),
#    ("2+4", 6),
#    ("6*9", 42),
# ])
# def test_eval(input, expected):
#    assert eval(input) == expected


# http://tetamap.wordpress.com/2009/05/13/parametrizing-python-tests-generalized/
def generate_params(funcarglist, keywords=None, genargs=None):
    """ Generative parameter decorator for test functions.

        Examples
        --------

        >>> from pkglib_testing.pytest.util import generate_params, pytest_generate_tests
        >>> @generate_params([dict(a=1, b=2), dict(a=3, b=3), dict(a=5, b=4)])
        ... def test_equals(a, b):
        ...     assert a == b
    """
    if not keywords:
        keywords = ()
    if not genargs:
        genargs = {}

    def wrapper(function):
        function.funcarglist = funcarglist
        function.keywords = keywords
        function.genargs = genargs
        return function
    return wrapper


def pytest_generate_tests(metafunc):
    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)


