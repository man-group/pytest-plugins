"""     Pytest general util stuff.
"""
from pkglib.testing.util import Workspace, TmpVirtualEnv, PkgTemplate, SVNRepo


# Note this is now supported natively in py.test using the following decorator
#@pytest.mark.parametrize(("input", "expected"), [
#    ("3+5", 8),
#    ("2+4", 6),
#    ("6*9", 42),
#])
#def test_eval(input, expected):
#    assert eval(input) == expected


# http://tetamap.wordpress.com/2009/05/13/parametrizing-python-tests-generalized/
def generate_params(funcarglist, keywords=None, genargs=None):
    """ Generative parameter decorator for test functions.

        Examples
        --------

        >>> from pkglib.testing.pytest.util import generate_params, pytest_generate_tests
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


def pytest_funcarg__workspace(request):
    """ Creates a temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=Workspace,
        teardown=lambda p: p.teardown(),
        scope='function',
    )


def pytest_funcarg__virtualenv(request):
    """ Creates a virtualenv in a temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=TmpVirtualEnv,
        teardown=lambda p: p.teardown(),
        scope='function',
    )


def pytest_funcarg__pkg_template(request):
    """ Create a new package from the core template in a temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=PkgTemplate,
        teardown=lambda p: p.teardown(),
        scope='function',
    )


def pytest_funcarg__svn_repo(request):
    """ Create a new svn repo in a temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=SVNRepo,
        teardown=lambda p: p.teardown(),
        scope='function',
    )
