'''
Created on 25 Apr 2012

@author: eeaston
'''
import os
from six.moves import configparser
import sys
import socket
import glob
import shutil
import threading

try:
    from path import Path
except ImportError:
    from path import path as Path

from wsgiref.simple_server import make_server
from paste.deploy.loadwsgi import loadapp
from pytest import yield_fixture

from pytest_server_fixtures.http import HTTPTestServer


class ConfigNotFoundError(Exception):
    """Raised when a given config file and path is not found."""


@yield_fixture(scope='session')
def pyramid_server(request):
    """ Session-scoped Pyramid server run in a subprocess, out of a temp dir. 
        This is a 'real' server that you can point a Selenium webdriver at.
    
        This fixture searches for its configuration in the current working directory
        called 'testing.ini'. All .ini files in the cwd will be copied to the tempdir
        so that config chaining still works. 
        
        The fixture implementation in `PyramidTestServer` has more flexible configuration
        options, use it directly to define more fine-grained fixtures. 
        
        Methods
        -------
        get_config() : Return current configuration as a dict.
        get()        : Query url relative to the server root.
        ..             Retry failures by default.
        post()       : Post payload to url relative to the server root.
        ..             Retry failures by default.
        
        Attributes
        ----------
        working_config  (`path.path`): Path to the config file used by the server at runtime
        .. also inherits all attributes from the `workspace` fixture 
    """
    with PyramidTestServer() as server:
        server.start()
        yield server


class PyramidTestServer(HTTPTestServer):
    port_seed = 65532

    def __init__(self, config_dir=None, config_filename=None, extra_config_vars=None, **kwargs):
        """ Test server for a Pyramid project

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
        self.original_config = Path(self.config_dir) / self.config_filename

        # Always print debug output for this process
        os.environ['DEBUG'] = '1'

        # Discover externally accessable hostname so selenium can get to it
        kwargs['hostname'] = kwargs.get('hostname', socket.gethostbyname(os.uname()[1]))

        super(PyramidTestServer, self).__init__(preserve_sys_path=True, **kwargs)

    def pre_setup(self):
        """ Make a copy of at the ini files and set the port number and host in the new testing.ini
        """
        self.working_config = self.workspace / self.config_filename

        # We need the other ini files as well here as they may be chained
        for filename in glob.glob(os.path.join(self.config_dir, '*.ini')):
            shutil.copy(filename, self.workspace)

        Path.copy(self.original_config, self.working_config)

        parser = configparser.ConfigParser()
        parser.read(self.original_config)
        parser.set('server:main', 'port', str(self.port))
        parser.set('server:main', 'host', self.hostname)
        [parser.set(section, k, v) for section, cfg in self.extra_config_vars.items() for (k, v) in cfg.items()]
        with open(str(self.working_config), 'w') as fp:
            parser.write(fp)

        try:
            parser.get('app:main', 'url_prefix')
        except configparser.NoOptionError:
            parser.set('app:main', 'url_prefix', '')

        # Set the uri to be the external hostname and the url prefix
        self._uri = "http://%s:%s/%s" % (os.uname()[1], self.port, parser.get('app:main', 'url_prefix'))

    @property
    def run_cmd(self):
        return [sys.executable, '-c', 'import sys; from pyramid.scripts.pserve import main; sys.exit(main())', self.working_config]

    def get_config(self):
        """ Convenience method to return our currently running config file as
            an items dictionary, skipping logging sections
        """
        # Use our workspace for %(here) expansion
        parser = configparser.ConfigParser({'here': self.workspace})
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
