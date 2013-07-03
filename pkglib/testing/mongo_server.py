import os
import tempfile
import shutil
import subprocess

import pymongo
from pymongo.errors import AutoReconnect, ConnectionFailure

from pkglib import CONFIG, config
from server import TestServer


class MongoTestServer(TestServer):
    # Use a random port for Mongo, as we could be running tests in parallel
    random_port = True  # Should we use a random port?

    def __init__(self, **kwargs):
        config.setup_org_config()
        mongod_dir = tempfile.mkdtemp(dir=self.get_base_dir())
        super(MongoTestServer, self).__init__(workspace=mongod_dir, **kwargs)

    @staticmethod
    def get_base_dir():
        candidate_dir = os.environ.get('WORKSPACE', None)
        if not candidate_dir or not os.path.exists(candidate_dir):
            candidate_dir = os.environ.get('TMPDIR', '/tmp')

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
                    '--logpath=%s/mongodb.log' % self.workspace,
                    '--nounixsocket',
                    '--smallfiles',
                    '--nohttpinterface',
                    '--nssize=1',
                    '--nojournal'
        ]

    def check_server_up(self):
        """Test connection to the server."""
        print "Connecting to Mongo at %s:%s" % (self.hostname, self.port)
        try:
            # TODO: update this to use new pymongo Client
            self.api = pymongo.Connection(self.hostname, self.port)
            return True
        except (AutoReconnect, ConnectionFailure), e:
            print e
        return False

    def kill(self):
        """ We override kill, as the parent kill does way too much.  We are
            single process and simply want to kill the underlying mongod process. """
        if self.server:
            try:
                self.server.exit = True
                self.server.p.kill()
                self.server.p.wait()
            except OSError:
                pass
            self.dead = True

    @staticmethod
    def kill_all():
        """ Helper method which will ensure that there are no running mongos on
            the current host, in the current workspace """
        base = MongoTestServer.get_base_dir()

        print "======================================"
        print "Cleaning up previous sessions under " + base
        print "======================================"

        for mongo in os.listdir(base):
            if mongo.startswith('tmp'):
                mongo = os.path.join(base, mongo)
                print "Previous session: " + mongo
                lock = os.path.join(mongo, 'mongod.lock')
                if os.path.exists(lock):
                    print "Lock file found: " + lock
                    p = subprocess.Popen(["lsof", "-Fp", "--", lock],
                                         stdout=subprocess.PIPE)
                    (out, _) = p.communicate()
                    if out:
                        pid = out[1:].strip()
                        print "Owned by pid: " + pid + " killing..."
                        p = subprocess.Popen(["kill -9 %s" % pid], shell=True)
                        p.communicate()
                print "Removing: " + mongo
                shutil.rmtree(mongo, True)

    def teardown(self):
        """ Called when tearing down this instance, eg in a context manager
        """
        self.delete = True
        super(MongoTestServer, self).teardown()
