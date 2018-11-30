"""
Implementation of how a server fixture will run.
"""

import os
import signal
import hashlib
import threading
import time
import subprocess
import logging
import docker
import socket
import traceback
import errno

from pytest_server_fixtures import CONFIG
from pytest_shutil.workspace import Workspace
from .base import get_ephemeral_host, ProcessReader, ServerNotDead, OSX

log = logging.getLogger(__name__)


def _merge_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


def _is_debug():
    return 'DEBUG' in os.environ and os.environ['DEBUG'] == '1'


class ServerClass(threading.Thread):
    """Example interface for ServerClass."""

    def __init__(self, get_cmd, env, hostname=None):
        """Initialise the server class.
        Server fixture will be started here.
        """
        super(ServerClass, self).__init__()

        # set serverclass thread to a daemon thread
        self.daemon = True

        self._get_cmd = get_cmd
        self._env = env
        self._hostname = hostname

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


class ThreadServer(ServerClass):
    """Thread server class."""

    def __init__(self, get_cmd, env, workspace, cwd=None):
        hostname = get_ephemeral_host()

        super(ThreadServer, self).__init__(
            get_cmd,
            env,
            hostname,
        )

        self.exit = False
        self._workspace = workspace
        self._cwd = cwd
        self._proc = None
        self._dead = False
        self._run_cmd = []

    def launch(self):
        log.debug("Launching thread server.")

        self._run_cmd = self._get_cmd(
            hostname=self._hostname,
            workspace=self._workspace,
        )

        args = dict(
            env=self._env,
            cwd=self._cwd,
            preexec_fn=os.setsid
        )

        debug = _is_debug()

        if debug:
            args['stdout'] = subprocess.PIPE
            args['stderr'] = subprocess.PIPE

        self._proc = subprocess.Popen(self._run_cmd, **args)

        if debug:
            ProcessReader(self._proc, self._proc.stdout, False).start()
            ProcessReader(self._proc, self._proc.stderr, True).start()

        self.start()

    def run(self):
        """Run in thread"""
        log.debug("Running server: %s" % ' '.join(self._run_cmd))
        log.debug("CWD: %s" % self._cwd)
        try:
            self._proc.wait()
        except OSError:
            if not self.exit:
                traceback.print_exc()

    def is_running(self):
        if not self._proc:
            return False
        return self._proc.poll() is None

    def teardown(self):
        if self._dead:
            log.debug("Already teardown, skip")
            return
        self._dead = True

        if not self._proc:
            log.warning("No process is running, skip teardown.")
            return

        if self._terminate():
            return

        if self._kill():
            return

        self._cleanup_all()

    def _terminate(self):
        log.debug("Terminating process")
        try:
            self._proc.terminate()
            if self._wait_for_process():
                return True
        except OSError as err:
            log.warning("Failed to terminate server.")
            log.debug(err)
            return False

    def _kill(self):
        log.debug("Killing process")
        try:
            self._proc.kill()
            if self._wait_for_process():
                return True
        except OSError as err:
            log.warning("Failed to kill server.")
            log.debug(err)
            return False

    def _cleanup_all(self):
        """
        Kill all child processes spawned with the same PGID
        """

        log.debug("Killing process group.")

        # Prevent traceback printed when the server goes away as we kill it
        self.exit = True

        try:
            pgid = os.getpgid(self._proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except OSError as err:
            log.debug(err)
            log.warning("Failed to cleanup processes. Giving up...")

    def _wait_for_process(self, interval=1, max_retries=10):
        retries = 0
        log.debug("Wait for process")
        while self.is_running():
            retries+=1
            log.debug("Still waiting for server to die (retries: %d)", retries)
            time.sleep(interval)
            if retries > max_retries:
                return False

        return True


class DockerServer(ServerClass):
    """Docker server class."""

    client = docker.from_env()

    def __init__(self, get_cmd, env, image, labels={}):
        super(DockerServer, self).__init__(get_cmd, env)

        self._image = image
        self._labels = _merge_dicts(labels, dict(session_id=CONFIG.session_id))

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

            log.debug('container is running at %s', self.hostname)


        except docker.errors.ImageNotFound as err:
            log.warning("Failed to start container, image %s not found", self.image)
            log.debug(err)
            raise
        except docker.errors.APIError as err:
            log.warning("Failed to start container")
            log.debug(err)
            raise

        self.start()

    def run(self):
        try:
            self._container.wait()
        except docker.errors.APIError:
            log.warning("Error while waiting for container.")
            log.debug(self._container.logs())

    def teardown(self):
        if not self._container:
            return

        try:
            self._container.stop()
            self._container.remove()
        except docker.errors.APIError:
            log.warning("Error when stopping the container.")

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
            log.warning("Failed when getting container status, container might have been removed.")
            return False


class KubernetesServer(ServerClass):
    """Kubernetes server class."""

    random_port = False

    def __init__(self, get_cmd, env, image):
        super(KubernetesServer, self).__init__(get_cmd, env)
        self._image = image

    def run(self):
        pass
