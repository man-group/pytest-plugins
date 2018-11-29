"""
Implementation of how a server fixture will run.
"""

import threading
import subprocess
import logging
import docker

from pytest_server_fixtures import CONFIG
from pytest_shutil.workspace import Workspace
from .base import get_ephemeral_host, get_ephemeral_port, ProcessReader

log = logging.getLogger(__name__)


def _merge_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


class ServerClass(threading.Thread):
    """Example interface for ServerClass."""

    def __init__(self, port, env=None):
        """Initialise the server class.
        Server fixture will be started here.
        """
        super(ServerClass, self).__init__()

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

    def __init__(self, port, image, labels={}, env={}):
        super(DockerServer, self).__init__(port, env)

        self._image = image
        self._labels = _merge_dicts(labels, dict(session_id=CONFIG.session_id))
        self._env = env
        self._container = None

    def launch(self):
        try:
            log.debug('launching container')
            self._container = DockerServer.client.containers.run(
                self._image,
                environment=self._env,
                labels=self._labels,
                detach=True,
            )

            while not self.is_running():
                log.debug('waiting for container to start')
                time.sleep(5)

            log.debug('container is running at %s:%d', self.hostname, self.port)


        except docker.errors.ImageNotFound as err:
            log.warn("Failed to start container, image %s not found", self.image)
            log.debug(err)
            raise
        except docker.errors.APIError as err:
            log.warn("Failed to start container")
            log.debug(err)
            raise

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
            self._container.remove()
        except docker.errors.APIError:
            log.warn("Error when stopping the container.")

    @property
    def hostname(self):
        if not self.is_running():
            return None
        return self._container.attrs['NetworkSettings']['IPAddress']

    def is_running(self):
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
