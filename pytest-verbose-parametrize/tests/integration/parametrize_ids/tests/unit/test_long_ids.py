import pytest


@pytest.mark.parametrize(('x', 'y', ), [(list(range(100)), None), ])
def test_foo(x, y):
    assert y not in x
