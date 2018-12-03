"""
Implementation of how a server fixture will run.
"""

import os
import signal
import threading
import time
import subprocess
import logging
import socket
import traceback
import errno
import uuid
import yaml

from retry import retry
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

    @property
    def hostname(self):
        """Get server's hostname."""
        return self._hostname


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

    def __init__(self, get_cmd, env, image, labels={}):
        # defer import of docker
        global docker
        import docker

        super(DockerServer, self).__init__(get_cmd, env)

        self._image = image
        self._labels = _merge_dicts(labels, {
            'server-fixture': 'docker-server-fixtures',
            'server-fixtures/session-id': CONFIG.session_id,
        })
        self._run_cmd = get_cmd()

        self._client = docker.from_env()
        self._container = None

    def launch(self):
        try:
            log.debug('launching container')
            self._container = self._client.containers.run(
                image=self._image,
                command=self._run_cmd,
                environment=self._env,
                labels=self._labels,
                detach=True,
                auto_remove=True,
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
    def image(self):
        return self._image

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

class KubernetesPodNotRunningException(Exception):
    """Thrown when a kubernetes pod is not in running state."""
    pass

class KubernetesPodNotTerminatedException(Exception):
    """Thrown when a kubernetes pod is still running."""
    pass

class KubernetesServer(ServerClass):
    """Kubernetes server class."""

    def __init__(self, get_cmd, env, image, labels={}):
        global ApiException
        global k8sclient
        from kubernetes import config
        from kubernetes import client as k8sclient
        from kubernetes.client.rest import ApiException

        config.load_kube_config()

        super(KubernetesServer, self).__init__(get_cmd, env)

        self._namespace = 'default'
        self._name = 'server-fixtures-%s' % uuid.uuid4()

        self._image = image
        self._run_cmd = get_cmd()
        self._labels = _merge_dicts(labels, {
            'server-fixtures': 'kubernetes-server-fixtures',
            'server-fixtures/session-id': CONFIG.session_id,
        })

        self._v1api = k8sclient.CoreV1Api()

    def launch(self):
        try:
            log.debug('%s Launching pod' % self._log_prefix)
            self._create_pod()
            self._wait_until_running()
            log.debug('%s Pod is running' % self._log_prefix)
        except:
            log.warning('%s Error while launching pod', self._log_prefix)
            raise

    def run(self):
        pass

    def teardown(self):
        self._delete_pod()
        # TODO: provide an flag to skip the wait to speed up the tests?
        self._wait_until_teardown()

    @property
    def image(self):
        return self._image

    @property
    def hostname(self):
        return self._get_pod_status().pod_ip

    @property
    def namespace(self):
        return self._namespace

    @property
    def name(self):
        return self._name

    def _get_pod_spec(self):
        container = k8sclient.V1Container(
            name='fixture',
            image=self.image,
            command=self._run_cmd
        )

        return k8sclient.V1PodSpec(
            containers=[container]
        )

    def _create_pod(self):
        try:
            pod = k8sclient.V1Pod()
            pod.metadata = k8sclient.V1ObjectMeta(name=self.name)
            pod.spec = self._get_pod_spec()
            self._v1api.create_namespaced_pod(namespace=self.namespace, body=pod)
        except ApiException as e:
            log.error("%s Failed to create pod: %s", self._log_prefix, e.reason)
            raise

    def _delete_pod(self):
        try:
            body = k8sclient.V1DeleteOptions()
            # delete the pod without waiting
            body.grace_period_seconds = 1
            self._v1api.delete_namespaced_pod(namespace=self.namespace, name=self.name, body=body)
        except ApiException as e:
            log.error("%s Failed to delete pod: %s", self._log_prefix, e.reason)

    def _get_pod_status(self):
        try:
            resp = self._v1api.read_namespaced_pod_status(namespace=self.namespace, name=self.name)
            return resp.status
        except ApiException as e:
            log.error("%s Failed to read pod status: %s", self._log_prefix, e.reason)
            raise

    @retry(KubernetesPodNotRunningException, tries=28, delay=1, backoff=2, max_delay=10)
    def _wait_until_running(self):
        current_phase = self._get_pod_status().phase
        log.debug("%s Waiting for pod status 'Running' (current='%s')", self._log_prefix, current_phase)
        if current_phase != 'Running':
            raise KubernetesPodNotRunningException()

    @retry(KubernetesPodNotTerminatedException, tries=28, delay=1, backoff=2, max_delay=10)
    def _wait_until_teardown(self):
        try:
            self._get_pod_status()
            raise KubernetesPodNotTerminatedException()
        except ApiException as e:
            if e.status == 404:
                return
            raise

    @property
    def _log_prefix(self):
        return "[K8S %s:%s]" % (self.namespace, self.name)
