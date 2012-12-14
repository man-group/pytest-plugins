from pkglib.testing.pytest.parametrize_ids import pytest_generate_tests
from mock import Mock


def test_generates_ids_from_tuple():
    p = Mock(kwargs={}, args=(None, [(1, 2, 3)]))
    metafunc = Mock()
    metafunc.function.parametrize = [p]
    pytest_generate_tests(metafunc)
    assert p.kwargs['ids'] == ['1-2-3']


def test_generates_ids_from_tuple_of_strings():
    p = Mock(kwargs={}, args=(None, [("11", "22", "33")]))
    metafunc = Mock()
    metafunc.function.parametrize = [p]
    pytest_generate_tests(metafunc)
    assert p.kwargs['ids'] == ['11-22-33']


def test_generates_ids_single_param():
    p = Mock(kwargs={}, args=("test_param", [1, 2, 3]))
    metafunc = Mock()
    metafunc.function.parametrize = [p]
    pytest_generate_tests(metafunc)
    assert p.kwargs['ids'] == ['1', '2', '3']


def test_generates_ids_single__string_param():
    p = Mock(kwargs={}, args=("test_param", ["111", "222", "333"]))
    metafunc = Mock()
    metafunc.function.parametrize = [p]
    pytest_generate_tests(metafunc)
    assert p.kwargs['ids'] == ['111', '222', '333']


def test_ok_on_non_parametrized_function():
    pytest_generate_tests(object())
