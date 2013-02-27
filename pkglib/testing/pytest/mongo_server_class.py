import pytest

from mongo_server import _mongo_server


@pytest.fixture(scope='class')
def mongo_server(request):
    """ Same as mongo_server fixture, scoped for test classes.
        This is in its own file here so we can keep the fixture name the same.
    """
    svr = _mongo_server(request)
    request.cls.mongo_server = svr
    return svr
