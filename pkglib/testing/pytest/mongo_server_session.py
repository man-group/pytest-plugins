""" Same as mongo_server fixture, scoped as session instead.
    This is in its own file here so we can keep the fixture name the same.
"""
import os
import pytest

from pkglib.testing.mongo_server import MongoTestServer

if 'WORKSPACE' in os.environ:
    MongoTestServer.kill_all()


@pytest.fixture(scope='session')
def mongo_server(request):
    test_server = MongoTestServer()
    request.addfinalizer(lambda p=test_server: p.teardown())
    return test_server
