"""
Thread server class implementation
"""
import logging
import subprocess
import os
import traceback
import signal
import time

from pytest_server_fixtures import CONFIG
from pytest_server_fixtures.base import get_ephemeral_host, ProcessReader, ServerNotDead, OSX
from .common import ServerClass, is_debug

log = logging.getLogger(__name__)


class ThreadServer(ServerClass):
    """Thread server class."""

    def __init__(self, get_cmd, env, workspace, cwd=None, random_hostname=True):
        super(ThreadServer, self).__init__(
            get_cmd,
            env,
            hostname=(get_ephemeral_host() if random_hostname else CONFIG.fixture_hostname),
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

        debug = is_debug()

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
        log.debug("Running server: %s", ' '.join(self._run_cmd))
        log.debug("CWD: %s", self._cwd)
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
