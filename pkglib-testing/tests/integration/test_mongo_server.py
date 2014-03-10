import pytest
pytest_plugins = ['pkglib_testing.pytest.mongo_server']


def test_mongo_server(mongo_server, mongo_host):
    assert mongo_server.check_server_up()
    assert mongo_server.delete
    mongo_server.api.db.test.insert({'a': 'b', 'c': 'd'})
    assert mongo_server.api.db.test.find_one({'a': 'b'}, fields={'_id': False}) == {'a': 'b', 'c': 'd'}
    assert mongo_host == "%s:%s" % (mongo_server.api.host, mongo_server.api.port)


@pytest.mark.parametrize('count', range(10))
def test_mongo_server_multi(count, mongo_server):
    coll = mongo_server.api.some_database.some_collection
    assert coll.count() == 0
    coll.insert({'a': 'b'})
    assert coll.count() == 1
