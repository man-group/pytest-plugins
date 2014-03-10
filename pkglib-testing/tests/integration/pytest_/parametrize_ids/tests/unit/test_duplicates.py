from pkglib_testing.pytest.parametrize_ids import pytest_generate_tests  # @UnusedImport  # NOQA
import pytest


@pytest.mark.parametrize(('x', 'y', ), [(0, [1]), (0, [1]), (str(0), str([1]))])
def test_foo(x, y):
    assert str([int(x) + 1]) == y
