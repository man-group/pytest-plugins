import pytest

from pkglib_testing.redis_server import RedisTestServer


def _redis_server(request):
    """ Does the redis server work, this is used within different scoped
        fixtures.
    """
    test_server = RedisTestServer()
    request.addfinalizer(lambda p=test_server: p.teardown())
    test_server.start()
    return test_server


@pytest.fixture(scope='function')
def redis_server(request):
    """ Boot up Redis in a local thread.
        This also provides a temp workspace.
        Function scoped.
    """
    return _redis_server(request)
