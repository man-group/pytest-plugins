import os
import hashlib
import logging
import time
from datetime import datetime

from pytest_server_fixtures import CONFIG
from pytest_shutil.workspace import Workspace
from .base import get_ephemeral_port
from .serverclass import create_server

log = logging.getLogger(__name__)


class TeardownTestServerException(Exception):
    """Thrown when attempting to start an already teardown test server."""
    pass


class TestServerV2(Workspace):
    """Base class of a v2 test server."""
    random_port = True
    random_hostname = True
    port_seed = 65535

    def __init__(self, cwd=None, workspace=None, delete=None, server_class=CONFIG.server_class):
        """
        Initialise a test server.

        @param cwd: the current working directory
        @param workspace: where all files will be stored
        @param delete: whether to delete the workspace after teardown or not
        @param server_class: specify server class name (default from CONFIG.server_class)
        """
        super(TestServerV2, self).__init__(workspace=workspace, delete=delete)
        self._cwd = cwd or os.getcwd()
        self._server_class = server_class
        self._server = None
        self._teardown = False

    def start(self):
        """
        Start the test server.
        """
        if self._teardown:
            raise TeardownTestServerException()

        try:
            self._server = create_server(
                server_class=CONFIG.server_class,
                server_type=self.__class__.__name__,
                get_cmd=self.get_cmd,
                env=self.env,
                image=self.image,
                workspace=self.workspace,
                cwd=self._cwd,
                random_hostname=self.random_hostname,
            )

            if self._server_class == 'thread':
                self.pre_setup()

            self._server.launch()
            self._wait_for_go()
            log.debug("Server now awake")

            self.post_setup()
        except OSError as err:
            log.warning("Error when starting the test server.")
            log.debug(err)
            raise

    def teardown(self):
        """
        Stop the server and clean up all resources.
        """
        if self._teardown:
            log.debug("Server is already teardown, skipping")
            return

        if not self._server:
            log.debug("Server not started yet, skipping")
            return
        self._server.teardown()
        self._server = None

        super(TestServerV2, self).teardown()

        self._teardown = True

    def check_server_up(self):
        """
        Check if the server is up.
        """
        raise NotImplementedError("Concret class should implement this")

    @property
    def hostname(self):
        """
        Get the IP address of the server.
        """
        return self._server.hostname

    @property
    def port(self):
        """
        Get the port number of the server.
        """
        raise NotImplementedError("Concret class should implement this")

    @property
    def cwd(self):
        """
        Get the current working directory of the server.
        """
        return self._cwd

    @property
    def image(self):
        """
        Get the Docker image of the server.
        """
        raise NotImplementedError("Concret class should implement this")

    @property
    def env(self):
        """
        Get the environment variables for running the server fixture.
        """
        return dict()

    def get_cmd(self, **kwargs):
        """
        Get the command to run the server fixtures.
        """
        raise NotImplementedError("Concrete class should implement this")

    def pre_setup(self):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def post_setup(self):
        """
        Set up step to be run after server is up.
        """
        pass

    def _wait_for_go(self, start_interval=0.1, retries_per_interval=3, retry_limit=28, base=2.0):
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

    def _get_port(self, default_port):
        """
        Get a random or pseudo-random port based on config.
        """
        if self._server_class != 'thread':
            return default_port

        return (
            get_ephemeral_port() if self.random_port
            else self._get_pseudo_random_port())

    def _get_pseudo_random_port(self):
        """
        Get a pseudo random port based on port_seed,
        classname and current username.
        """
        sig = (os.environ['USER'] + self.__class__.__name__).encode('utf-8')
        return self.port_seed - int(hashlib.sha1(sig).hexdigest()[:3], 16)
