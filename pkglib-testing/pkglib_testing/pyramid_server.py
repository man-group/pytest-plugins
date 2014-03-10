'''
Created on 25 Apr 2012

@author: eeaston
'''
import os
import ConfigParser
import sys
import socket
import glob
import shutil
import threading
import time
import requests
from path import path

from six.moves import http_client
from wsgiref.simple_server import make_server
from paste.deploy.loadwsgi import loadapp

from server import HTTPTestServer


class ConfigNotFoundError(Exception):
    """Raised when a given config file and path is not found."""


class PyramidTestServer(HTTPTestServer):
    port_seed = 65532

    def __init__(self, config_dir=None, config_filename=None, extra_config_vars=None, **kwargs):
        """  Test server for a Pyrarmid project

        Parameters
        ----------
        config_dir:
            Path to a directory to find the config file/s. Defaults to current working dir, and
            all .ini files in the directory will be made available for config file chaining.
        config_filename:
            Name of the main config file to use. Defaults to testing.ini.
        extra_config_vars:
            Dict of any extra entries to add to the file, as { section: { key: value } }
        """
        self.extra_config_vars = extra_config_vars if extra_config_vars is not None else {}
        self.config_dir = config_dir if config_dir is not None else os.getcwd()
        self.config_filename = config_filename if config_filename else 'testing.ini'

        self.working_config = None
        self.original_config = path(self.config_dir) / self.config_filename

        # Always print debug output for this process
        os.environ['DEBUG'] = '1'

        # Discover externally accessable hostname so selenium can get to it
        kwargs['hostname'] = kwargs.get('hostname', socket.gethostbyname(os.uname()[1]))

        super(PyramidTestServer, self).__init__(**kwargs)

    def pre_setup(self):
        """ Make a copy of at the ini files and set the port number and host in the new testing.ini
        """
        self.working_config = self.workspace / self.config_filename

        # We need the other ini files as well here as they may be chained
        for filename in glob.glob(os.path.join(self.config_dir, '*.ini')):
            shutil.copy(filename, self.workspace)

        path.copy(self.original_config, self.working_config)

        parser = ConfigParser.ConfigParser()
        parser.read(self.original_config)
        parser.set('server:main', 'port', self.port)
        parser.set('server:main', 'host', self.hostname)
        [parser.set(section, k, v) for section, cfg in self.extra_config_vars.items() for (k, v) in cfg.items()]
        with self.working_config.open('w') as fp:
            parser.write(fp)

        # Set the uri to be the external hostname and the url prefix
        self._uri = "http://%s:%s/%s" % (os.uname()[1], self.port, parser.get('app:main', 'url_prefix'))

    @property
    def run_cmd(self):
        return [path(sys.exec_prefix) / 'bin' / 'python', path(sys.exec_prefix) / 'bin' / 'pserve', self.working_config]

    def query_url(self, path, as_json=True, attempts=25):
        '''Queries url and returns the string returns, cnoverted to python equivalent of json if json=True.
        Path argument should be whatever comes after 'http://hostname:port/'.
        '''
        for i in range(attempts):
            try:
                returned = requests.get('http://%s:%d/%s' % (self.hostname, self.port, path))
                if as_json:
                    return returned.json()
                return returned
            except (http_client.BadStatusLine, requests.ConnectionError) as e:
                time.sleep(int(i) / 10)
                pass
        raise e

    def post_to_url(self, path, data=None, attempts=25, as_json=True):
        for i in range(attempts):
            try:
                returned = requests.post('http://%s:%d/%s' % (self.hostname, self.port, path), data=data)
                if as_json:
                    return returned.json()
                return returned
            except (http_client.BadStatusLine, requests.ConnectionError) as e:
                time.sleep(int(i) / 10)
                pass
        raise e

    def get_config(self):
        """ Convenience method to return our currently running config file as
            an items dictionary, skipping logging sections
        """
        # Use our workspace for %(here) expansion
        parser = ConfigParser.ConfigParser({'here': self.workspace})
        parser.read(self.config)
        return dict([(section, dict(parser.items(section)))
                     for section in parser.sections()
                     if not section.startswith('logger')
                     and not section.startswith('formatter')
                     and not section.startswith('handler')])


class InlinePyramidTestServer(PyramidTestServer):
    random_port = True
    port_seed = None

    def start_server(self, env=None):
        """ Start the server instance.
        """
        print('\n==================================================================================')
        print("Starting wsgiref pyramid test server on host %s port %s" % (self.hostname, self.port))
        wsgi_app = loadapp('config:' + self.working_config)
        self.server = make_server(self.hostname, self.port, wsgi_app)
        worker = threading.Thread(target=self.server.serve_forever)
        worker.daemon = True
        worker.start()
        self.wait_for_go()
        print("Server now awake")
        print('==================================================================================')

    def kill(self):
        if self.server:
            print('\n==================================================================================')
            print("Stopping wsgiref pyramid test server on host %s port %s" % (self.hostname, self.port))
            print('==================================================================================')
            self.server.shutdown()
            self.server = None
