from ahl.testing.httpd_proxy_server import HTTPDProxyServer


def test_httpd_proxy_server():
    server = HTTPDProxyServer()
    server.start()
    assert server.check_server_up()
    server.kill()
    assert not server.check_server_up()
