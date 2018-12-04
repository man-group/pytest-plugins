"""
Common utils for all serverclasses
"""
import os
import threading

def merge_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


def is_debug():
    return 'DEBUG' in os.environ and os.environ['DEBUG'] == '1'


class ServerFixtureNotRunningException(Exception):
    """Thrown when a kubernetes pod is not in running state."""
    pass

class ServerFixtureNotTerminatedException(Exception):
    """Thrown when a kubernetes pod is still running."""
    pass

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
