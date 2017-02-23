import os
import tempfile
import shutil
import subprocess
import time
import errno
import logging
import getpass

import pytest

from pytest_server_fixtures import CONFIG
from pytest_fixture_config import yield_requires_config

from .base import TestServer

log = logging.getLogger(__name__)


def _mongo_server():
    """ This does the actual work - there are several versions of this used
        with different scopes.
    """
    test_server = MongoTestServer()
    try:
        test_server.start()
        yield test_server
    finally:
        test_server.teardown()


@yield_requires_config(CONFIG, ['mongo_bin'])
@pytest.yield_fixture(scope='function')
def mongo_server():
    """ Function-scoped MongoDB server started in a local thread.
        This also provides a temp workspace.
        We tear down, and cleanup mongos at the end of the test.

        For completeness, we tidy up any outstanding mongo temp directories
        at the start and end of each test session

        Attributes
        ----------
        api (`pymongo.MongoClient`)  : PyMongo Client API connected to this server
        .. also inherits all attributes from the `workspace` fixture
    """
    for server in _mongo_server():
        yield server


@yield_requires_config(CONFIG, ['mongo_bin'])
@pytest.yield_fixture(scope='session')
def mongo_server_sess():
    """ Same as mongo_server fixture, scoped as session instead.
    """
    for server in _mongo_server():
        yield server


@yield_requires_config(CONFIG, ['mongo_bin'])
@pytest.yield_fixture(scope='class')
def mongo_server_cls(request):
    """ Same as mongo_server fixture, scoped for test classes.
    """
    for server in _mongo_server():
        request.cls.mongo_server = server
        yield server


@yield_requires_config(CONFIG, ['mongo_bin'])
@pytest.yield_fixture(scope='module')
def mongo_server_module():
    """ Same as mongo_server fixture, scoped for test modules.
    """
    for server in _mongo_server():
        yield server


class MongoTestServer(TestServer):
    # Use a random port for Mongo, as we run tests in parallel
    random_port = True

    def __init__(self, **kwargs):
        mongod_dir = tempfile.mkdtemp(dir=self.get_base_dir())
        super(MongoTestServer, self).__init__(workspace=mongod_dir, delete=True, **kwargs)

    @staticmethod
    def get_base_dir():
        candidate_dir = os.environ.get('WORKSPACE', None)
        if not candidate_dir or not os.path.exists(candidate_dir):
            candidate_dir = os.environ.get('TMPDIR', '/tmp')

        candidate_dir = os.path.join(candidate_dir, getpass.getuser(), 'mongo')
        if not os.path.exists(candidate_dir):
            try:
                os.makedirs(candidate_dir)
            except OSError as exc:  # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(candidate_dir):
                    pass
                else:
                    raise
        return candidate_dir

    @property
    def run_cmd(self):
        return ['%s/mongod' % CONFIG.mongo_bin,
                '--bind_ip=%s' % self.hostname,
                '--port=%s' % self.port,
                '--dbpath=%s' % self.workspace,
                '--nounixsocket',
                '--syncdelay', '0',
                '--nohttpinterface',
                '--nojournal',
                '--quiet',
                '--storageEngine=ephemeralForTest'
                ]

    def check_server_up(self):
        """Test connection to the server."""
        import pymongo
        from pymongo.errors import AutoReconnect, ConnectionFailure

        log.info("Connecting to Mongo at %s:%s" % (self.hostname, self.port))
        try:
            self.api = pymongo.MongoClient(self.hostname, self.port,
                                           serverselectiontimeoutms=200)
            self.api.database_names()
            # Configure the client with default timeouts in case the server goes slow
            self.api = pymongo.MongoClient(self.hostname, self.port)
            return True
        except (AutoReconnect, ConnectionFailure) as e:
            pass
        return False

    def kill(self):
        """ We override kill, as the parent kill does way too much.  We are single process
            and simply want to kill the underlying mongod process. """
        if self.server:
            try:
                self.server.exit = True
                self.server.p.kill()
                self.server.p.wait()
                i = 0
                while self.check_server_up():
                    time.sleep(0.1)
                    if i % 10 == 0:
                        log.info("Waiting for MongoServer.kill()")
            except OSError:
                pass
            self.dead = True

    @staticmethod
    def cleanup_all():
        """Helper method which will ensure that there are no running mongos
        on the current host, in the current workspace"""
        base = MongoTestServer.get_base_dir()

        log.info("======================================")
        log.info("Cleaning up previous sessions under " + base)
        log.info("======================================")

        for mongo in os.listdir(base):
            if mongo.startswith('tmp'):
                mongo = os.path.join(base, mongo)
                log.info("Previous session: " + mongo)
                lock = os.path.join(mongo, 'mongod.lock')
                if os.path.exists(lock):
                    log.info("Lock file found: " + lock)
                    p = subprocess.Popen(["/usr/sbin/lsof", "-Fp", "--", lock], stdout=subprocess.PIPE)
                    (out, _) = p.communicate()
                    if out:
                        pid = out[1:].strip()
                        log.info("Owned by pid: " + pid + " killing...")
                        p = subprocess.Popen(["kill -9 %s" % pid], shell=True)
                        p.communicate()
                log.info("Removing: " + mongo)
                shutil.rmtree(mongo, True)


# Cleanup any old mongo sessions for this workspace when run in Jenkins
# We do this here rather than doing:
#    request.cached_setup(MongoTestServer.kill_all, scope='session')
# as with pytest-xidst, the per-session setups appear to be run for each worker

# We don't do this for users (who don't have the WORKSPACE env variable set)
# as they may legitimately be running a test suite more than once.

# TODO: check that with the latest py.test this is still the case, work has
#       been done to improve fixtures with xdist
if 'WORKSPACE' in os.environ:
    MongoTestServer.cleanup_all()
