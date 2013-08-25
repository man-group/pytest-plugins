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


class ConfigNotFoundError(Exception):
    """Raised when a given config file and path is not found."""


class PyramidTestServer(HTTPTestServer):
    port_seed = 65532

    def __init__(self, **kwargs):
        self.config = None
        self.original_config = None

        self.testing_ini = kwargs.get("testing_ini")

        # Always print debug output for this process
        os.environ['DEBUG'] = '1'

        # Discover externally accessable hostname so selenium can get to it
        kwargs['hostname'] = kwargs.get('hostname',
                                        socket.gethostbyname(os.uname()[1]))

        super(PyramidTestServer, self).__init__(**kwargs)

    def pre_setup(self):
        """ Make a copy of the development and testing ini file and set the
            port number and host
        """
        # We need the development.ini as well here as they are chained
        if not self.testing_ini:
            dev_cfg = path(os.getcwd()) / 'development.ini'
            dev_cfg_copy = self.workspace / 'development.ini'
            path.copy(dev_cfg, dev_cfg_copy)

            self.original_config = path(os.getcwd()) / 'testing.ini'
            self.config = self.workspace / 'testing.ini'
            path.copy(self.original_config, self.config)

        else:
            if not os.path.isfile(self.testing_ini):
                raise ConfigNotFoundError(
                    "{0} not found".format(self.testing_ini)
                )

            # development_ini isn't used if you have set testing_ini

            # Copy the original file and reuse its file name. The given file
            # name should be distinct in the dir it will get copied to!
            self.original_config = path(self.testing_ini)
            cfg_filename = os.path.basename(self.testing_ini)
            self.config = self.workspace / cfg_filename
            path.copy(self.original_config, self.config)

        parser = ConfigParser.ConfigParser()
        # self.original_config only refers to testing.ini, development.ini
        # isn't used?
        parser.read(self.original_config)
        parser.set('server:main', 'port', self.port)
        parser.set('server:main', 'host', self.hostname)
        with self.config.open('w') as fp:
            parser.write(fp)

        # Set the uri to be the external hostname and the optional url prefix
        parts = ["http:/", "{}:{}".format(os.uname()[1], self.port)]
        if parser.has_option('app:main', 'url_prefix'):
            parts.append(parser.get('app:main', 'url_prefix'))
        self._uri = "/".join(parts)

    @property
    def run_cmd(self):
        return [path(sys.exec_prefix) / 'bin' / 'pserve', self.config]

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
