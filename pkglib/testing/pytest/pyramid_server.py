from pkglib.testing.pyramid_server import PyramidTestServer


def pytest_funcarg__pyramid_server(request):
    """ Boot up Redis in a local thread.
        This also provides a temp workspace.
    """
    return request.cached_setup(
        setup=PyramidTestServer,
        teardown=lambda p: p.teardown(),
        scope='session',
    )
