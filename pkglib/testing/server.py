from datetime import datetime
import os
import random
import subprocess
import threading
import time
import traceback
import hashlib
from urllib2 import urlopen, URLError
import socket


from util import Workspace


class ServerThread(threading.Thread):
    """ Class for running the server in a thread """

    def __init__(self, hostname, port, run_cmd, run_stdin=None):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.port = port
        self.run_cmd = run_cmd
        self.run_stdin = run_stdin
        self.daemon = True
        self.exit = False
        if 'DEBUG' in os.environ:
            self.p = subprocess.Popen(self.run_cmd,
                                      stdin=subprocess.PIPE
                                      if run_stdin else None)
        else:
            self.p = subprocess.Popen(self.run_cmd,
                                      stdin=subprocess.PIPE
                                      if run_stdin else None,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)

    def run(self):
        print "Running server: %s" % ' '.join(self.run_cmd)
        print "CWD: %s" % os.getcwd()
        try:
            self.p.communicate(input=self.run_stdin)
        except OSError:
            if not self.exit:
                traceback.print_exc()


class TestServer(Workspace):
    """ Abstract class for creating a working dir and
        setting up a server instance in a thread,
    """
    server = None
    # Child classes can set this to a different serverthread class
    serverclass = ServerThread

    port_seed = 65535  # Used to seed port numbers - see below
    random_port = False  # Should we use a random port?
    hostname = '127.0.0.1'

    def __init__(self, **kwargs):
        super(TestServer, self).__init__(workspace=kwargs.get('workspace',
                                                              None))

        self.port = kwargs.get('port', self.get_port())
        self.hostname = kwargs.get('hostname', self.hostname)
        # We don't know if the server is alive or dead at this point,
        # assume we are alive
        self.dead = False

        self.kill()

        try:
            self.pre_setup()
            self.start_server()
            self.post_setup()
            self.save()
        except:
            self.teardown()
            raise

    def get_port(self):
        """
        Pick repeatable but semi-random port based on hashed username, and the
        server class.
        """
        port = (self.port_seed -
                int(hashlib.sha1(os.environ['USER'] +
                                 self.__class__.__name__).hexdigest()[:3], 16))
        if self.random_port:
            port += random.randrange(1000)
        return port

    def pre_setup(self):
        """ This should execute any setup required before starting the server
        """
        pass

    @property
    def run_cmd(self):
        """ Child classes should implement this to return the commands needed
            to start the server
        """
        raise NotImplementedError("Concrete class should implement this")

    @property
    def run_stdin(self):
        """ This is passed to the server as stdin
        """
        return None

    def post_setup(self):
        """ This should execute any setup required after starting the server
        """
        pass

    def check_server_up(self):
        """ This is called to see if the server is up
        """
        raise NotImplementedError("Concrete class should implement this")

    def wait_for_go(self, start_interval=0.1, retries_per_interval=3,
                    retry_limit=21):
        """
        This is called to wait until the server has started running.

        Uses a binary exponential backoff algorithm to set wait interval
        between retries. This finds the happy medium between quick starting
        servers (e.g. in-memory DBs) while remaining useful for the slower
        starting servers (e.g. web servers).

        Arguments
        ---------
        start_interval: initial wait interval
        retries_per_interval: number of retries before increasing waiting time.
        retry_limit: total number of retries to attempt before giving up.

        """
        if start_interval <= 0.0:
            raise ValueError('start interval must be positive!')

        interval = start_interval

        retry_count = retry_limit
        start_time = datetime.now()
        while retry_count > 0:
            for _ in range(retries_per_interval):
                print 'sleeping for %s before retrying (%d of %d)' \
                    % (interval, ((retry_limit + 1) - retry_count), retry_limit)
                if self.check_server_up():
                    print 'waited %s for server to start successfully' \
                        % str(datetime.now() - start_time)
                    return
                time.sleep(interval)
                retry_count -= 1
            interval *= 2.0

        if not retry_count:
            raise ValueError("Server failed to start up after waiting {}. "
                             "Giving up!".format(datetime.now() - start_time))

    def start_server(self):
        """ Start the server instance.
        """
        print "Starting Server on host %s port %s" % (self.hostname, self.port)
        self.server = self.serverclass(self.hostname, self.port, self.run_cmd,
                                       self.run_stdin)
        self.server.start()
        self.wait_for_go()
        print "Server now awake"
        self.dead = False

    def kill(self, retries=5):
        """ Kill all running versions of this server.
            Just killing the thread.server pid isn't good enough, it might
            spawn children
        """
        # Prevent traceback printed when the server goes away as we kill it
        if self.server:
            self.server.exit = True
        if not self.dead:
            cycles = 0
            while True:
                print "Waiting for server to die.."
                ip_addr = socket.gethostbyname(self.hostname)

                # Uncomment these to debug the pid tracing
                #self.run("netstat -anp 2>/dev/null", check_rc=False)
                #self.run("netstat -anp 2>/dev/null | grep {0}:{1}"
                #         .format(ip_addr, self.port), check_rc=False)
                #self.run("netstat -anp 2>/dev/null | grep {0}:{1} | "
                #         "grep LISTEN".format(ip_addr, self.port),
                #         check_rc=False)
                #self.run("netstat -anp 2>/dev/null | grep {0}:{1} | "
                #         "grep LISTEN | awk '{{ print $7 }}'"
                #         .format(ip_addr, self.port), check_rc=False)

                ps = [p.strip() for p in
                      self.run("netstat -anp 2>/dev/null | grep {0}:{1} | "
                               "grep LISTEN | awk '{{ print $7 }}' | "
                               "cut -d'/' -f1".format(ip_addr, self.port),
                               capture=True).split('\n') if p.strip()]
                print "process IDs: %s" % ps
                if ps:
                    for p in ps:
                        try:
                            int(p)
                        except ValueError:
                            print("Can't determine port, process shutting down"
                                  " or owned by someone else")
                        else:
                            self.run("kill -9 %s" % p, check_rc=False)
                else:
                    print "No PIDs, server is dead"
                    break
                cycles += 1
                if cycles >= retries:
                    raise ValueError("Server not dead after {} retries"
                                     .format(retries))
                time.sleep(1)
        self.dead = True

    def teardown(self):
        """ Called when tearing down this instance, eg in a context manager
        """
        self.kill()
        super(TestServer, self).teardown()

    def save(self):
        """ Called to save any state that can be then restored using
            self.restore
        """
        pass

    def restore(self):
        """ Called to restore any state that was saved using using self.save
        """
        pass


class HTTPTestServer(TestServer):

    def __init__(self, uri=None, **kwargs):
        self._uri = uri
        super(HTTPTestServer, self).__init__(**kwargs)

    @property
    def uri(self):
        if self._uri:
            return self._uri
        return "http://%s:%s" % (self.hostname, self.port)

    def check_server_up(self):
        """ Check the server is up by polling self.uri
        """
        try:
            print 'accessing URL:', self.uri
            urlopen(self.uri)
            return True
        except URLError, e:
            print "Server not up yet (%s).." % e
            return False