from mock import Mock

from pytest_verbose_parametrize import pytest_generate_tests


def get_metafunc(args):
    p = Mock(kwargs={}, args=args)
    p._arglist = ([args, {}],)
    metafunc = Mock()
    metafunc.function.parametrize = p
    return metafunc

def test_generates_ids_from_tuple():
    metafunc = get_metafunc((None, [(1, 2, 3)]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['1-2-3']


def test_generates_ids_from_tuple_of_strings():
    metafunc = get_metafunc((None, [("11", "22", "33")]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['11-22-33']


def test_truncates_args_tuple():
    metafunc = get_metafunc((None, [tuple(range(100))]))
    pytest_generate_tests(metafunc)
    kwargs = metafunc.function.parametrize.kwargs
    assert len(kwargs['ids'][0]) == 64
    assert kwargs['ids'][0].endswith('...')


def test_generates_ids_single_param():
    metafunc = get_metafunc(("test_param", [1, 2, 3]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['1', '2', '3']


def test_generates_ids_single__string_param():
    metafunc = get_metafunc(("test_param", ["111", "222", "333"]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['111', '222', '333']


def test_truncates_single_arg():
    metafunc = get_metafunc((None, ["1" * 100]))
    pytest_generate_tests(metafunc)
    kwargs = metafunc.function.parametrize.kwargs
    assert len(kwargs['ids'][0]) == 32
    assert kwargs['ids'][0].endswith('...')


def test_generates_ids_from_duplicates():
    metafunc = get_metafunc((None, [(1, 2, 3), (1, 2, 3)]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['1-2-3', '1-2-3#1']


def test_generates_ids_from_apparent_duplicates():
    metafunc = get_metafunc((None, [(1, 2, 3), ('1', '2', '3')]))
    pytest_generate_tests(metafunc)
    assert metafunc.function.parametrize.kwargs['ids'] == ['1-2-3', '1-2-3#1']


def test_ok_on_non_parametrized_function():
    pytest_generate_tests(object())
