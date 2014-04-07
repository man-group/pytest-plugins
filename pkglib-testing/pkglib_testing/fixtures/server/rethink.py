import socket

import pytest
import rethinkdb

from pkglib_testing import CONFIG

from .base import TestServer
from ..util import requires_config


def _rethink_server(request):
    """ This does the actual work - there are several versions of this used
        with different scopes.
    """
    test_server = RethinkDBServer()
    request.addfinalizer(lambda p=test_server: p.teardown())
    test_server.start()
    return test_server


@requires_config(['rethink_executable'])
@pytest.fixture(scope='function')
def rethink_server(request):
    """ Function-scoped RethinkDB server in a local thread.
    """
    return _rethink_server(request)


@requires_config(['rethink_executable'])
@pytest.fixture(scope='session')
def rethink_server_sess(request):
    """ Same as rethink_server fixture, scoped as session instead.
    """
    return _rethink_server(request)


class RethinkDBServer(TestServer):
    random_port = True

    def __init__(self, **kwargs):
        super(RethinkDBServer, self).__init__(**kwargs)
        self.cluster_port = self.get_port()
        self.http_port = self.get_port()
        self.db = None

    @property
    def run_cmd(self):
        return [CONFIG.rethink_executable,
                '--directory', self.workspace / 'db',
                '--bind', socket.gethostbyname(self.hostname),
                '--driver-port', str(self.port),
                '--http-port', str(self.http_port),
                '--cluster-port', str(self.cluster_port),
        ]

    def check_server_up(self):
        """Test connection to the server."""
        print("Connecting to RethinkDB at %s:%s" % (self.hostname, self.port))
        try:
            self.conn = rethinkdb.connect(host=self.hostname, port=self.port, db='test')
            return True
        except rethinkdb.RqlDriverError as e:
            print(e)
        return False