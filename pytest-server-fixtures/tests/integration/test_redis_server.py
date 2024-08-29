def test_server_runner(redis_server):
    """ Boot up a server, push some keys into it
    """
    assert redis_server.check_server_up()
    redis_server.api.set('foo', 'bar')
    assert redis_server.api.get('foo').decode('utf8') == 'bar'
