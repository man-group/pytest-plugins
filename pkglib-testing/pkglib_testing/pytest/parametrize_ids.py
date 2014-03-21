from collections import Iterable
from pkglib.six import string_types


def _strize_arg(arg):
    try:
        s = arg.__name__
    except AttributeError:
        s = str(arg)
    if len(s) > 32:
        s = s[:29] + '...'
    return s


def pytest_generate_tests(metafunc):
    """
    pytest_generate_tests hook to generate ids for parametrized tests that are
    better than the default (which just outputs id numbers).

    Example::

        from pkglib_testing.pytest.parametrize_ids import pytest_generate_tests
        import pytest

        @pytest.mark.parametrize(('f', 't'), [(sum, list), (len, int)])
        def test_foo(f, t):
            assert isinstance(f([[1], [2]]), t)

    In this example, the test ids will be generated as 'test_foo[sum-list]',
    'test_foo[len-int]' instead of the default 'test_foo[1-2]', 'test_foo[3-4]'.

    """
    try:
        param = metafunc.function.parametrize
    except AttributeError:
        return
    for p in param:
        if 'ids' not in p.kwargs:
            list_names = []
            for i, argvalue in enumerate(p.args[1]):
                if (not isinstance(argvalue, Iterable)) or isinstance(argvalue, string_types):
                    argvalue = (argvalue,)
                name = '-'.join(_strize_arg(arg) for arg in argvalue)
                if len(name) > 64:
                    name = name[:61] + '...'
                while name in list_names:
                    name = '%s#%d' % (name, i)
                list_names.append(name)
            p.kwargs['ids'] = list_names
