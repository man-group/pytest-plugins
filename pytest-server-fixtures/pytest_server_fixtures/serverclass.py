"""
Implementation of how a server fixture will run.
"""

import threading
import subprocess
import logging
import docker

from pytest_shutil.workspace import Workspace
from .base import get_ephemeral_host, get_ephemeral_port, ProcessReader

log = logging.getLogger(__name__)


class ServerClass(threading.Thread):
    """Example interface for ServerClass."""

    def __init__(self, port, env=None):
        """Initialise the server class.
        Server fixture will be started here.
        """

        # set serverclass thread to a daemon thread
        self.daemon = True

        self._hostname = None
        self._port = port
        self._workspace = None

    def run(self):
        """In a new thread, wait for the server to return."""
        pass

    def launch(self):
        """Start the server."""
        pass

    def teardown(self):
        """Kill the server."""
        pass

    def is_running(self):
        """Check if the server is running."""
        pass

    @property
    def hostname(self):
        """Get server's hostname."""
        return self._hostname

    @property
    def port(self):
        """Get server's port."""
        return self._port


class ThreadServer(ServerClass):
    """Thread server class."""

    def __init__(self, run_cmd, port, cwd, env=None, random_port=True, pre_setup=None, post_setup=None, kill=None):
        super(ThreadServer, self).__init__(port, env)

        self._hostname = get_ephemeral_host()
        self._port = get_ephemeral_port(host=self._hostname) if random_port else port

        self.exit = False
        self.env = env or dict(os.environ)
        self.cwd = cwd

    def launch(self):
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

        self.start()

    def run(self):
        """Run in thread"""
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

    def teardown(self):
        pass


class DockerServer(ServerClass):
    """Docker server class."""

    client = docker.from_env()

    def __init__(self, image, port, labels={}, env={}):
        self._image = image
        self._env = env
        self._labels = labels
        self._container = None

    def launch(self):
        try:
            self._container = DockerServer.client.containers.run(
                self.image,
                environment=self._env,
                labels=self._labels,
                detach=True,
            )
        except docker.errors.ImageNotFound:
            log.warn("Failed to start container, image %s not found", self.image)
        except docker.errors.APIError:
            log.warn("Failed to start container")

        self.start()

    def run(self):
        try:
            self._container.wait()
        except docker.errors.APIError:
            log.warn("Error while waiting for container.")
            log.debug(self._container.logs())

    def teardown(self):
        if not self._container:
            return

        try:
            self._container.stop()
        except docker.errors.APIError:
            log.warn("Error when stopping the container.")

    def hostname(self):
        if not self._is_running():
            return None
        else:
            return self._container.attrs['NetworkSettings']['IPAddress']

    def get_workspace(self):
        pass

    def _is_running(self):
        if not self._container:
            return False

        try:
            self._container.reload()
            return self._container.status == 'running'
        except docker.errors.APIError:
            log.warn("Failed when getting container status, container might have been removed.")
            return False


class KubernetesServer(ServerClass):
    """Kubernetes server class."""

    def __init__(self, image, env=None):
        pass

    def run(self):
        pass
