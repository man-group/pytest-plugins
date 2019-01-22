import pytest


def test_mongo_server(mongo_server):
    assert mongo_server.check_server_up()
    assert mongo_server.delete
    mongo_server.api.db.test.insert({'a': 'b', 'c': 'd'})
    assert mongo_server.api.db.test.find_one({'a': 'b'}, {'_id': False}) == {'a': 'b', 'c': 'd'}


@pytest.mark.parametrize('count', range(3))
def test_mongo_server_multi(count, mongo_server):
    coll = mongo_server.api.some_database.some_collection
    assert coll.count() == 0
    coll.insert({'a': 'b'})
    assert coll.count() == 1
