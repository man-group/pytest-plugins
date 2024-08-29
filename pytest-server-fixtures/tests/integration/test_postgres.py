import pytest

def test_postgres_server(postgres_server_sess):
    conn = postgres_server_sess.connect('integration')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")
    cursor.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
    cursor.execute("SELECT * FROM test;")
    assert cursor.fetchone() == (1, 100, "abc'def")


