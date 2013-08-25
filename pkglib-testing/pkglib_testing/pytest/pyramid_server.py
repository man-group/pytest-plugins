import pytest

from pkglib_testing.pyramid_server import PyramidTestServer


@pytest.fixture(scope='session')
def pyramid_server(request):
    """ Boot up a Pyramid server in a local thread.
    """
    server = PyramidTestServer()
    request.addfinalizer(lambda: server.teardown())
    server.start()
    return server
