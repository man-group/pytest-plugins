"""
Thread server class implementation
"""
import logging
import os
import signal
import subprocess
import traceback
import time
import psutil

from retry import retry

from pytest_server_fixtures import CONFIG
from pytest_server_fixtures.base import get_ephemeral_host, ProcessReader, ServerNotDead, OSX
from .common import ServerClass, is_debug

log = logging.getLogger(__name__)


class ProcessStillRunningException(Exception):
    pass


@retry(ProcessStillRunningException,
       tries=15,
       delay=1)
def _wait_for_all(procs):
    log.debug("Waiting for %d processes to die", len(procs))
    gone, alive = psutil.wait_procs(procs, timeout=1)

    if len(alive) == 0:
        log.debug("All processes are terminated")
        return

    log.warning("%d processes remainings: %s", len(alive), ",".join(alive))
    raise ProcessStillRunningException()


def _kill_proc_tree(pid, sig=signal.SIGKILL, timeout=None):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    children.append(parent)
    log.debug("Killing process tree for %d (total_procs_to_kill=%d)", parent.pid, len(children))
    for p in children:
        p.send_signal(sig)
    _wait_for_all(children)


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
        if not self._proc:
            log.warning("No process is running, skip teardown.")
            return

        _kill_proc_tree(self._proc.pid)
        self._proc = None

