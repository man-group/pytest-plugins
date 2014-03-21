from __future__ import print_function

import hashlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime

from pkglib.six import string_types
from pkglib.six.moves import http_client
from pkglib.six.moves.urllib.request import urlopen
from pkglib.six.moves.urllib.error import URLError

from .util import Workspace


def get_ephemeral_port():
    """ Get an ephemeral socket at random from the kernel
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ProcessReader(threading.Thread):
    def __init__(self, process, stream, stderr):
        self.stderr = stderr
        self.process = process
        self.stream = stream
        super(ProcessReader, self).__init__()
        self.setDaemon(True)

    def run(self):
        while self.process.poll() is None:
            l = self.stream.readline()
            if not isinstance(l, string_types):
                l = l.decode('utf-8')

            if self.stderr:
                sys.stderr.writelines(l.strip() + "\n")
            else:
                print(l.strip())


class ServerThread(threading.Thread):
    """ Class for running the server in a thread """

    def __init__(self, hostname, port, run_cmd, run_stdin=None, env=None, cwd=None):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.port = port
        self.run_cmd = run_cmd
        self.run_stdin = run_stdin
        self.daemon = True
        self.exit = False
        self.env = env or dict(os.environ)
        self.cwd = cwd or os.getcwd()

        if 'DEBUG' in os.environ:
            self.p = subprocess.Popen(self.run_cmd, env=self.env, cwd=self.cwd,
                                      stdin=subprocess.PIPE if run_stdin else None)
        else:
            self.p = subprocess.Popen(self.run_cmd, env=self.env, cwd=self.cwd,
                                      stdin=subprocess.PIPE if run_stdin else None,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            ProcessReader(self.p, self.p.stdout, False).start()
            ProcessReader(self.p, self.p.stderr, True).start()

    def run(self):
        print("Running server: %s" % ' '.join(self.run_cmd))
        print("CWD: %s" % self.cwd)
        try:
            if self.run_stdin:
                self.p.stdin.write(self.run_stdin.encode('utf-8'))
            if self.p.stdin:
                self.p.stdin.close()
            self.p.wait()
        except OSError:
            if not self.exit:
                traceback.print_exc()


class TestServer(Workspace):
    """ Abstract class for creating a working dir and
        setting up a server instance in a thread,
    """
    server = None
    serverclass = ServerThread  # Child classes can set this to a different serverthread class
    hostname = socket.gethostname()  # Not using localhost in case this is used in a cluster-type job

    random_port = True  # Use a random or fixed port number
    port_seed = 65535  # Used to seed port numbers if not random_port

    kill_signal = signal.SIGTERM

    def __init__(self, workspace=None, delete=None, **kwargs):
        super(TestServer, self).__init__(workspace=workspace, delete=delete)
        self.port = kwargs.get('port', self.get_port())
        self.hostname = kwargs.get('hostname', self.hostname)
        # We don't know if the server is alive or dead at this point, assume alive
        self.dead = False
        self.env = kwargs.get('env')
        self.cwd = kwargs.get('cwd')

    def start(self):
        self.kill()
        try:
            self.pre_setup()
            self.start_server(env=self.env)
            self.post_setup()
            self.save()
        except:
            self.teardown()
            raise

    def get_port(self):
        """
        Pick repeatable but semi-random port based on hashed username, and the server class.
        """
        if not self.random_port:
            return self.port_seed - int(hashlib.sha1((os.environ['USER']
                                                      + self.__class__.__name__).encode('utf-8')).hexdigest()[:3], 16)
        return get_ephemeral_port()

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

    def wait_for_go(self, start_interval=0.1, retries_per_interval=3, retry_limit=28, base=2.0):
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
                print('sleeping for %s before retrying (%d of %d)'
                      % (interval, ((retry_limit + 1) - retry_count), retry_limit))
                if self.check_server_up():
                    print('waited %s for server to start successfully'
                          % str(datetime.now() - start_time))
                    return
                time.sleep(interval)
                retry_count -= 1
            interval *= base

        raise ValueError("Server failed to start up after waiting %s. Giving up!"
                         % str(datetime.now() - start_time))

    def start_server(self, env=None):
        """ Start the server instance.
        """
        print("Starting Server on host %s port %s" % (self.hostname, self.port))
        self.server = self.serverclass(self.hostname, self.port, self.run_cmd, self.run_stdin,
                                       env=getattr(self, "env", env), cwd=self.cwd)
        self.server.start()
        self.wait_for_go()
        print("Server now awake")
        self.dead = False

    def kill(self, retries=5):
        """ Kill all running versions of this server.
            Just killing the thread.server pid isn't good enough, it might spawn children
        """
        # Prevent traceback printed when the server goes away as we kill it
        if self.server:
            self.server.exit = True

        if self.dead:
            return

        cycles = 0
        while True:
            print("Waiting for server to die..")

            netstat_cmd = ("netstat -anp 2>/dev/null | grep %s:%s | grep LISTEN | "
                           "awk '{ print $7 }' | cut -d'/' -f1" % (socket.gethostbyname(self.hostname), self.port))
            ps = [p.strip() for p in self.run(netstat_cmd, capture=True, cd='/').split('\n') if p.strip()]
            print("process IDs: %s" % ps)

            if ps:
                for p in ps:
                    try:
                        p = int(p)
                    except ValueError:
                        print("Can't determine port, process shutting down or owned by someone else")
                    else:
                        os.kill(p, self.kill_signal)
            else:
                print("No PIDs, server is dead")
                break
            cycles += 1
            if cycles >= retries:
                raise ValueError("Server not dead after %d retries" % retries)
            time.sleep(1)

    def teardown(self):
        """ Called when tearing down this instance, eg in a context manager
        """
        self.kill()
        super(TestServer, self).teardown()

    def save(self):
        """ Called to save any state that can be then restored using self.restore
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
            print('accessing URL:', self.uri)
            url = urlopen(self.uri)
            return url.getcode() == 200
        except (URLError, socket.error, http_client.BadStatusLine) as e:
            if getattr(e, 'code', None) == 403:
                # This is OK, the server is probably running in secure mode
                return True
            print("Server not up yet (%s).." % e)
            return False


class SimpleHTTPTestServer(HTTPTestServer):
    """A Simple HTTP test server that serves up a folder of files over the web."""

    def __init__(self, workspace=None, delete=None, **kwargs):
        kwargs.pop("hostname", None)  # User can't set the hostname it is always 0.0.0.0
        # If we don't pass hostname="0.0.0.0" to our superclass's initialiser then the cleanup
        # code in kill won't work correctly. We don't set self.hostname however as we want our
        # uri property to still be correct.
        super(SimpleHTTPTestServer, self).__init__(workspace=workspace, delete=delete, hostname="0.0.0.0", **kwargs)
        self.cwd = self.file_dir

    @property
    def uri(self):
        if self._uri:
            return self._uri
        return "http://%s:%s" % (socket.gethostname(), self.port)

    @property
    def run_cmd(self):
        return ["python", "-m", "SimpleHTTPServer", str(self.port)]

    @property
    def file_dir(self):
        """This is the folder of files served up by this SimpleHTTPServer"""
        file_dir = os.path.join(str(self.workspace), "files")
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        return file_dir
