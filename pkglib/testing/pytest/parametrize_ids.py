from collections import Iterable


def pytest_generate_tests(metafunc):
    """
    pytest_generate_tests hook to generate ids for parametrized tests that are
    better than the default (which just outputs id numbers).

    Example::

        from pkglib.testing.pytest.parametrize_ids import pytest_generate_tests
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
            for argvalue in p.args[1]:
                if isinstance(argvalue, Iterable) and not isinstance(argvalue, basestring):
                    list_names.append('-'.join(getattr(arg, '__name__', str(arg)) for arg in argvalue))
                else:
                    list_names.append(getattr(argvalue, '__name__', str(argvalue)))
            p.kwargs['ids'] = list_names
