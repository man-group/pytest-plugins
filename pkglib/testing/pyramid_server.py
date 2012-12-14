'''
Created on 25 Apr 2012

@author: eeaston
'''
import os
import ConfigParser
import sys
import socket

from path import path

from server import HTTPTestServer


class PyramidTestServer(HTTPTestServer):
    port_seed = 65532

    def __init__(self, **kwargs):
        self.config = None
        self.original_config = None

        # Always print debug output for this process
        os.environ['DEBUG'] = '1'

        # Discover externally accessable hostname so selenium can get to it
        kwargs['hostname'] = kwargs.get('hostname', socket.gethostbyname(os.uname()[1]))

        super(PyramidTestServer, self).__init__(**kwargs)

    def pre_setup(self):
        """ Make a copy of the development and testing ini file and set the port number and host
        """
        # We need the development.ini as well here as they are chained
        dev_cfg = path(os.getcwd()) / 'development.ini'
        dev_cfg_copy = self.workspace / 'development.ini'
        path.copy(dev_cfg, dev_cfg_copy)

        self.original_config = path(os.getcwd()) / 'testing.ini'
        self.config = self.workspace / 'testing.ini'
        path.copy(self.original_config, self.config)

        parser = ConfigParser.ConfigParser()
        parser.read(self.original_config)
        parser.set('server:main', 'port', self.port)
        parser.set('server:main', 'host', self.hostname)
        with self.config.open('w') as fp:
            parser.write(fp)

        # Set the uri to be the external hostname and the url prefix
        self._uri = "http://%s:%s/%s" % (os.uname()[1], self.port, parser.get('app:main', 'url_prefix'))

    @property
    def run_cmd(self):
        return [path(sys.exec_prefix) / 'bin' / 'pserve', self.config]
