import os

from pytest_server_fixtures import CONFIG
from .serverclass import ThreadServer, DockerServer, KubernetesServer


class TestServerV2(Workspace):
    """Base class of a v2 test server."""

    def __init__(self, cwd=None, workspace=None, delete=None):
        """
        Initialise a test server.

        @param cwd: the current working directory
        @param workspace: where all files will be stored
        @param delete: whether to delete the workspace after teardown or not
        """
        super(TestServerV2, self).__init__(workspace=worksapce, delete=delete)
        self._cwd = cwd or os.getcwd()
        self._server = None
        self._dead = False

    def start(self):
        """
        Start the test server.
        """
        server_class = CONFIG.server_class

        try:
            self.server = self._create_server(server_class)

            if (server_class == 'thread'):
                self.pre_setup()

            self.server.launch()
            self.server._wait_for_go()
            log.debug("Server now awake")
            self._dead = False

            self.post_setup()
        except:
            self.teardown()
            raise

    def teardown(self):
        """
        Stop the server and clean up all resources.
        """
        if self.server:
            self.server.teardown()

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
        if not self._server:
            return None
        return self._server.hostname

    @property
    def port(self):
        """
        Get the port number of the server.
        """
        if not self._server:
            return -1
        return self._server.port

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
        pass

    @property
    def default_env(self):
        """
        Get the default environment variables.
        """
        return []

    @property
    def run_cmd(self):
        """DEPRECATED: only used if serverclass=thread"""
        raise NotImplementedError("Concrete class should implement this")

    def pre_setup(self):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def post_setup(self):
        pass

    def kill(self, retries=5):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def _create_server(self, server_class):
        """
        Initialise a server class instance
        """

        if server_class == 'thread':
            return ThreadServer(self.run_cmd, default_port, self.pre_setup, self.kill)
        elif server_class == 'docker':
            return DockerServer(self.image, self.default_env)
        elif server_class == 'kubernetes':
            return KubernetesServer(self.image, self.default_env)
        else:
            raise "Invalid server class: {}".format(server_class)

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
