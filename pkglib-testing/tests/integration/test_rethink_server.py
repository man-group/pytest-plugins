pytest_plugins = ['pkglib_testing.fixtures.server.rethink']


def test_rethink_server(rethink_server):
    assert rethink_server.check_server_up()
    assert rethink_server.conn.db == 'test'