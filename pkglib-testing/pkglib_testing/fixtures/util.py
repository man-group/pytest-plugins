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


def requires_config(vars_):
    """ Decorator for fixtures that will skip tests if the required config variables
        are missing from pkglib_testing.CONFIG
    """
    def decorator(f):
        # We need to specify 'request' in the args here to satisfy pytest's fixture logic
        @functools.wraps(f)
        def wrapper(request, *args, **kwargs):
            for var in vars_:
                if not getattr(CONFIG, var):
                    pytest.skip('pkglib_testing config variable {} missing, skipping test'.format(var))
            return f(request, *args, **kwargs)
        return wrapper
    return decorator
