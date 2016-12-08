import socket
import uuid
import logging

import pytest

from pytest_server_fixtures import CONFIG
from pytest_fixture_config import requires_config

from .base import TestServer


log = logging.getLogger(__name__)
rethinkdb = None


def _rethink_server(request):
    """ This does the actual work - there are several versions of this used
        with different scopes.
    """
    test_server = RethinkDBServer(hostname=CONFIG.fixture_hostname)
    request.addfinalizer(lambda p=test_server: p.teardown())
    test_server.start()
    return test_server


@requires_config(CONFIG, ['rethink_executable'])
@pytest.fixture(scope='function')
def rethink_server(request):
    """ Function-scoped RethinkDB server in a local thread.

        Attributes
        ----------
        conn: (``rethinkdb.Connection``)  Connection to this server instance
        .. also inherits all attributes from the `workspace` fixture

    """
    return _rethink_server(request)


@requires_config(CONFIG, ['rethink_executable'])
@pytest.fixture(scope='session')
def rethink_server_sess(request):
    """ Same as rethink_server fixture, scoped as session instead.
    """
    return _rethink_server(request)


@pytest.yield_fixture(scope="function")
def rethink_unique_db(rethink_server_sess):
    """ Starts up a session-scoped server, and returns a connection to
        a unique database for the life of a single test, and drops it after
    """
    dbid = uuid.uuid4().hex
    conn = rethink_server_sess.conn
    rethinkdb.db_create(dbid).run(conn)
    conn.use(dbid)
    yield conn
    rethinkdb.db_drop(dbid).run(conn)


@pytest.yield_fixture(scope="module")
def rethink_module_db(rethink_server_sess):
    """ Starts up a module-scoped server, and returns a connection to
        a unique database for all the tests in one module.
        Drops the database after module tests are complete.
    """
    dbid = uuid.uuid4().hex
    conn = rethink_server_sess.conn
    log.info("Making database")
    rethinkdb.db_create(dbid).run(conn)
    conn.use(dbid)
    yield conn
    log.info("Dropping database")
    rethinkdb.db_drop(dbid).run(conn)


@pytest.fixture(scope="module")
def rethink_make_tables(request, rethink_module_db):
    """ Module-scoped fixture that creates all tables specified in the test
        module attribute FIXTURE_TABLES.

    """
    reqd_table_list = getattr(request.module, 'FIXTURE_TABLES')
    log.debug("Do stuff before all module tests with {0}".format(reqd_table_list))
    conn = rethink_module_db
    for table_name, primary_key in reqd_table_list:
        try:
            rethinkdb.db(conn.db).table_create(table_name,
                                               primary_key=primary_key,
                                               ).run(conn)
            log.info('Made table "{0}" with key "{1}"'
                     .format(table_name, primary_key))
        except rethinkdb.errors.RqlRuntimeError as err:
            log.debug('Table "{0}" not made: {1}'.format(table_name, err.message))


@pytest.yield_fixture(scope="function")
def rethink_empty_db(request, rethink_module_db, rethink_make_tables):
    """ Function-scoped fixture that will empty all the tables defined
        for the `rethink_make_tables` fixture.

        This is a useful approach, because of the long time taken to
        create a new RethinkDB table, compared to the time to empty one.
    """
    tables_to_emptied = (table[0] for table
                         in getattr(request.module, 'FIXTURE_TABLES'))
    conn = rethink_module_db

    for table_name in tables_to_emptied:
        rethinkdb.db(conn.db).table(table_name).delete().run(conn)
        log.debug('Emptied "{0}" before test'.format(table_name))
    yield conn


class RethinkDBServer(TestServer):
    random_port = True

    def __init__(self, **kwargs):
        global rethinkdb
        try:
            import rethinkdb
        except ImportError:
            pytest.skip('rethinkdb not installed, skipping test')
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
        log.info("Connecting to RethinkDB at {0}:{1}".format(
            self.hostname, self.port))
        try:
            self.conn = rethinkdb.connect(host=self.hostname,
                                          port=self.port, db='test')
            return True
        except rethinkdb.RqlDriverError as err:
            log.warn(err)
        return False
