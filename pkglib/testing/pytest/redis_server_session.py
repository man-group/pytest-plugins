import pytest

from redis_server import _redis_server


@pytest.fixture(scope='session')
def redis_server(request):
    """ Same as redis_server fixture, scoped as session instead.
        This is in its own file here so we can keep the fixture name the same.
    """
    return _redis_server(request)
