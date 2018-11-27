from pytest_server_fixtures import CONFIG
from .serverclass import ThreadServer, DockerServer, KubernetesServer

def _merge_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z

class TestServerV2(object):
    """Base class of a v2 test server."""

    default_port = -1

    def __init__(self):
        self.server = None
        self.dead = False

    def start(self):
        try:
            self.server = self._create_server()
            self.server.launch()
            self.server.wait_for_go()
            log.debug("Server now awake")
            self.dead = False
        except:
            self.teardown()
            raise

    def teardown(self):
        self.server.teardown()

    def check_server_up(self):
        raise NotImplementedError("Concret class should implement this")

    @property
    def hostname(self):
        if self.server == None:
            return None
        return self.server.hostname

    @property
    def port(self):
        if self.server = None:
            return -1
        return self.server.port

    @property
    def cwd(self):
        if self.server = None:
            return None
        return self.server.cwd

    @property
    def image(self):
        pass

    @property
    def default_env(self):
        return []

    @property
    def run_cmd(self):
        """DEPRECATED: only used if serverclass=thread"""
        raise NotImplementedError("Concrete class should implement this")

    def pre_setup(self):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def post_setup(self):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def kill(self, retries=5):
        """DEPRECATED: only used if serverclass=thread"""
        pass

    def _create_server(self):
        """Initialise a server class instance"""
        server_class = CONFIG.server_class

        if server_class == 'thread':
            return ThreadServer(self.run_cmd, default_port, self.pre_setup, self.post_setup, self.kill)
        elif server_class == 'docker':
            return DockerServer(self.image, self.default_env)
        elif server_class == 'kubernetes':
            return KubernetesServer(self.image, self.default_env)
        else:
            raise "Invalid server class: {}".format(server_class)

    def _wait_for_go(self, start_interval=0.1, retries_per_interval=3, retry_limit=28, base=2.0):
        pass

