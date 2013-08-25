import pytest

from mongo_server import _mongo_server


@pytest.fixture(scope='session')
def mongo_server(request):
    """ Same as mongo_server fixture, scoped as session instead.
        This is in its own file here so we can keep the fixture name the same.
    """
    return _mongo_server(request)
