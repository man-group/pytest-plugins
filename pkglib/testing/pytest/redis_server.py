from pkglib.testing.redis_server import RedisTestServer


def pytest_funcarg__redis_server(request):
    """ Boot up Redis in a local thread.
        This also provides a temp workspace.
    """
    return request.cached_setup(
        setup=RedisTestServer,
        teardown=lambda p: p.teardown(),
        scope='session',
    )
