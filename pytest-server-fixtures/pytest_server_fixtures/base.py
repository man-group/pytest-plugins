""" Base classes for all server fixtures.
"""
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
import logging

from six import string_types

from pytest_server_fixtures import CONFIG
from pytest_shutil.workspace import Workspace

log = logging.getLogger(__name__)


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

            if l.strip():
                if self.stderr:
                    sys.stderr.writelines(l.strip() + "\n")
                else:
                    log.debug(l.strip())


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
        log.debug("Running server: %s" % ' '.join(self.run_cmd))
        log.debug("CWD: %s" % self.cwd)
        try:
            if self.run_stdin:
                log.debug("STDIN: %s" % self.run_stdin)
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

    random_port = True  # Use a random or fixed port number
    port_seed = 65535  # Used to seed port numbers if not random_port
    kill_signal = signal.SIGTERM

    # Number of seconds to wait between kill retries. Increase if the service takes a while to die
    kill_retry_delay = 1

    def __init__(self, workspace=None, delete=None, preserve_sys_path=False, **kwargs):
        super(TestServer, self).__init__(workspace=workspace, delete=delete)
        self.port = kwargs.get('port', self.get_port())
        self.hostname = kwargs.get('hostname', CONFIG.fixture_hostname)
        # We don't know if the server is alive or dead at this point, assume alive
        self.dead = False
        self.env = kwargs.get('env')
        self.cwd = kwargs.get('cwd')

        if preserve_sys_path:
            # If the child class was installed as a test dependency, the python dist files might not
            # be properly installed and subprocesses won't find them. When this flag is set
            # we preserve our full sys.path in PYTHONPATH to make sure the child process can still
            # import things properly
            env = self.env or dict(os.environ)
            env['PYTHONPATH'] = os.pathsep.join(sys.path)
            self.env = env

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

        Parameters
        ----------
        start_interval: ``float``
            initial wait interval in seconds
        retries_per_interval: ``int``
            number of retries before increasing waiting time
        retry_limit: ``int``
            total number of retries to attempt before giving up
        base: ``float``
            backoff multiplier

        """
        if start_interval <= 0.0:
            raise ValueError('start interval must be positive!')

        interval = start_interval

        retry_count = retry_limit
        start_time = datetime.now()
        while retry_count > 0:
            for _ in range(retries_per_interval):
                log.debug('sleeping for %s before retrying (%d of %d)'
                      % (interval, ((retry_limit + 1) - retry_count), retry_limit))
                if self.check_server_up():
                    log.debug('waited %s for server to start successfully'
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
        log.debug("Starting Server on host %s port %s" % (self.hostname, self.port))
        self.server = self.serverclass(self.hostname, self.port, self.run_cmd, self.run_stdin,
                                       env=getattr(self, "env", env), cwd=self.cwd)
        self.server.start()
        self.wait_for_go()
        log.debug("Server now awake")
        self.dead = False

    def kill(self, retries=5):
        """Kill all running versions of this server.

        Just killing the thread.server pid isn't good enough, it may
        have spawned children.

        """
        # Prevent traceback printed when the server goes away as we kill it
        if self.server:
            self.server.exit = True

        if self.dead:
            return

        # Wait for server to die.
        for _ in range(retries):
            netstat_cmd = ("netstat -anp 2>/dev/null | grep %s:%s | grep LISTEN | "
                           "awk '{ print $7 }' | cut -d'/' -f1" % (socket.gethostbyname(self.hostname), self.port))
            pids = [p.strip() for p in self.run(netstat_cmd, capture=True, cd='/').split('\n') if p.strip()]

            if not pids:
                # No PIDs remaining, server has died.
                break

            for pid in pids:
                try:
                    pid = int(pid)
                except ValueError:
                    # Can't determine process ID, process shutting down or owned by someone else.
                    pass
                else:
                    os.kill(pid, self.kill_signal)

            time.sleep(self.kill_retry_delay)
        else:
            raise ValueError("Server not dead after %d retries" % retries)

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
