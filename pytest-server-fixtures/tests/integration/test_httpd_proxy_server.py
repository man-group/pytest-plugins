
def test_httpd_proxy_server(httpd_server):
    assert httpd_server.check_server_up()
    httpd_server.kill()
    assert not httpd_server.check_server_up()
