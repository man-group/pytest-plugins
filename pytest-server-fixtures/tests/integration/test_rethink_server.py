def test_rethink_server(rethink_server):
    assert rethink_server.check_server_up()
    assert rethink_server.conn.db == 'test'


FIXTURE_TABLES = [('tbl_foo', 'code'), ('tbl_bar', 'id')]

# Lots of tests needed here!

def test_rethink_empty_db(rethink_empty_db):
    pass

def test_foo_1(rethink_empty_db):
    assert 1

def test_foo_2(rethink_empty_db):
    assert 2

def test_foo_3(rethink_empty_db):
    assert 3