import os
import tempfile
import shutil
import subprocess

import pytest

from pytest_server_fixtures import CONFIG
from pytest_fixture_config import requires_config

from .base import TestServer


def _mongo_server(request):
    """ This does the actual work - there are several versions of this used
        with different scopes.
    """
    test_server = MongoTestServer()
    request.addfinalizer(lambda p=test_server: p.teardown())
    test_server.start()
    return test_server


@requires_config(CONFIG, ['mongo_bin'])
@pytest.fixture(scope='function')
def mongo_server(request):
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
    return _mongo_server(request)


@requires_config(CONFIG, ['mongo_bin'])
@pytest.fixture(scope='session')
def mongo_server_sess(request):
    """ Same as mongo_server fixture, scoped as session instead.
    """
    return _mongo_server(request)


@requires_config(CONFIG, ['mongo_bin'])
@pytest.fixture(scope='class')
def mongo_server_cls(request):
    """ Same as mongo_server fixture, scoped for test classes.
    """
    svr = _mongo_server(request)
    request.cls.mongo_server = svr
    return svr


class MongoTestServer(TestServer):
    # Use a random port for Mongo, as we run tests in parallel
    random_port = True

    def __init__(self, **kwargs):
        global pymongo
        try:
            import pymongo
        except ImportError:
            pytest.skip('pymongo not installed, skipping test')
        mongod_dir = tempfile.mkdtemp(dir=self.get_base_dir())
        super(MongoTestServer, self).__init__(workspace=mongod_dir, delete=True, **kwargs)

    @staticmethod
    def get_base_dir():
        candidate_dir = os.environ.get('WORKSPACE', None)
        if not candidate_dir or not os.path.exists(candidate_dir):
            candidate_dir = os.environ.get('TMDDIR', '/tmp')

        candidate_dir = os.path.join(candidate_dir, 'mongo')
        if not os.path.exists(candidate_dir):
            os.mkdir(candidate_dir)
        return candidate_dir

    @property
    def run_cmd(self):
        return ['%s/mongod' % CONFIG.mongo_bin,
                '--bind_ip=%s' % self.hostname,
                '--port=%s' % self.port,
                '--dbpath=%s' % self.workspace,
                '--nounixsocket',
                '--smallfiles',
                '--syncdelay', '0',
                '--nohttpinterface',
                '--nssize=1',
                '--nojournal',
                '--quiet',
                ]

    def check_server_up(self):
        """Test connection to the server."""
        print("Connecting to Mongo at %s:%s" % (self.hostname, self.port))
        try:
            self.api = pymongo.MongoClient(self.hostname, self.port)
            return True
        except (pymongo.AutoReconnect, pymongo.ConnectionFailure) as e:
            print(e)
        return False

    def kill(self):
        """ We override kill, as the parent kill does way too much.  We are single process
            and simply want to kill the underlying mongod process. """
        if self.server:
            try:
                self.server.exit = True
                self.server.p.kill()
                self.server.p.wait()
            except OSError:
                pass
            self.dead = True

    @staticmethod
    def cleanup_all():
        """Helper method which will ensure that there are no running mongos
        on the current host, in the current workspace"""
        base = MongoTestServer.get_base_dir()

        print("======================================")
        print("Cleaning up previous sessions under " + base)
        print("======================================")

        for mongo in os.listdir(base):
            if mongo.startswith('tmp'):
                mongo = os.path.join(base, mongo)
                print("Previous session: " + mongo)
                lock = os.path.join(mongo, 'mongod.lock')
                if os.path.exists(lock):
                    print("Lock file found: " + lock)
                    p = subprocess.Popen(["/usr/sbin/lsof", "-Fp", "--", lock], stdout=subprocess.PIPE)
                    (out, _) = p.communicate()
                    if out:
                        pid = out[1:].strip()
                        print("Owned by pid: " + pid + " killing...")
                        p = subprocess.Popen(["kill -9 %s" % pid], shell=True)
                        p.communicate()
                print("Removing: " + mongo)
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
