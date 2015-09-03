import pytest_listener.server as li

RECEIVE_TIMEOUT = 10


def test_send_method(listener):
    obj = ['hello', 'world']
    listener.send(obj)
    d = listener.receive(RECEIVE_TIMEOUT)
    assert d == obj


def test_send_method_again(listener):
    test_send_method(listener)


def test_multiple_data(listener):
    obj1 = ['hello', 'world']
    listener.send(obj1)
    obj2 = 'fred'
    listener.send(obj2)

    d = listener.receive(RECEIVE_TIMEOUT)
    assert d == obj1
    d = listener.receive(RECEIVE_TIMEOUT)
    assert d == obj2


def test_send_halfway_data(listener):
    li.DEBUG = True
    try:
        obj1 = ['first', 'message']
        listener.send(obj1)

        obj2 = 'second'
        listener.send(obj2)

        d = listener.receive(RECEIVE_TIMEOUT)
        assert d == obj1

        listener.clear_queue()

        obj3 = 'third'
        listener.send(obj3)
        d = listener.receive(RECEIVE_TIMEOUT)
        assert d == obj3  # demonstrating that obj2 has been "removed"

    finally:
        li.DEBUG = False
