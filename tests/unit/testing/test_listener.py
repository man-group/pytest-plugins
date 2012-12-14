import socket
import json
from time import sleep

import pkglib.testing.listener as li

RECEIVE_TIMEOUT = 10

def setup_module(module):
    module.s = li.Listener()
    module.s.start()

def teardown_module(module):
    li.stop_listener(module.s)


def test_send_method():

    obj = ['hello', 'world']
    s.send(obj)
    d = s.receive(RECEIVE_TIMEOUT)
    assert d == obj
    assert s.port >= li.PORT


def test_send_method_again():
    test_send_method()


def test_multiple_data():
    obj1 = ['hello', 'world']
    s.send(obj1)
    obj2 = 'fred'
    s.send(obj2)

    d = s.receive(RECEIVE_TIMEOUT)
    assert d == obj1
    d = s.receive(RECEIVE_TIMEOUT)
    assert d == obj2


def test_send_halfway_data():
    li.DEBUG = True
    try:
        obj1 = ['first', 'message']
        s.send(obj1)

        obj2 = 'second'
        s.send(obj2)

        d = s.receive(RECEIVE_TIMEOUT)
        assert d == obj1

        s.clear_queue()

        obj3 = 'third'
        s.send(obj3)
        d = s.receive(RECEIVE_TIMEOUT)
        assert d == obj3 # demonstrating that obj2 has been "removed"

    finally:
        li.DEBUG = False
