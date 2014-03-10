import pytest
from pkglib_testing.server import SimpleHTTPTestServer


@pytest.yield_fixture
def simple_http_test_server():
    with SimpleHTTPTestServer() as s:
        s.start()
        yield s
