import pytest

from pkglib_testing.fixtures.server.httpd_proxy import HTTPDProxyServer

@pytest.mark.skipif(True, reason="TODO - make this work for stock ubuntu")
def test_httpd_proxy_server():
    server = HTTPDProxyServer()
    server.start()
    assert server.check_server_up()
    server.kill()
    assert not server.check_server_up()
