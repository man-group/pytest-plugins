from pkglib.testing.pytest.mongo_server import mongo_server


def test_mongo_server(mongo_server):
    assert mongo_server.check_server_up()
