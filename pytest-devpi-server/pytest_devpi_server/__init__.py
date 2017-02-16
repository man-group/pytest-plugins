'''
Created on 25 Apr 2012

@author: eeaston
'''
import os
import sys
import zipfile
import logging
from six.moves import cStringIO

import pkg_resources
from pytest import yield_fixture, fixture
import devpi_server as _devpi_server
from devpi.main import main as devpi_client
from pytest_server_fixtures.http import HTTPTestServer

log = logging.getLogger(__name__)


@yield_fixture(scope='session')
def devpi_server(request):
    """ Session-scoped Devpi server run in a subprocess, out of a temp dir. 
        Out-of-the-box it creates a single user an index for that user, then
        uses that index.
        
        Methods
        -------
        api():    Client API method, directly bound to the devpi-client command-line tool.  Examples:   
        ...          api('index', '-c', 'myindex') to create an index called 'myindex'
        ...          api('getjson', '/user/myindex') to return the json string describing this index
        
        Attributes
        ----------
        uri:          Server URI
        user:         Initially created username
        password:     Initially created password
        index:        Initially created index name
        server_dir:   Path to server database
        client_dir:   Path to client directory
           
        .. also inherits all attributes from the `workspace` fixture 
        
        For more fine-grained control over these attributes, use the class directly and pass in
        constructor arguments.
    """
    with DevpiServer() as server:
        server.start()
        yield server


@fixture
def devpi_function_index(request, devpi_server):
    """ Creates and activates an index for your current test function. 
    """
    index_name = '/'.join((devpi_server.user, request.function.__name__))
    devpi_server.api('index', '-c', index_name)
    devpi_server.api('use', index_name)
    return index_name


class DevpiServer(HTTPTestServer):

    def __init__(self, offline=True, debug=False, data=None, user="testuser", password="", index='dev', **kwargs):
        """ Devpi Server instance.

        Parameters
        ----------
        offline :  `bool`
            Run in offline mode. Defaults to True
        data:  `str`
           Filesystem path to a zipfile archive of the initial server data directory.
           If not set and in offline mode, it uses a pre-canned snapshot of a 
           newly-created empty server.
        """
        self.debug = debug
        if os.getenv('DEBUG') in (True, '1', 'Y', 'y'):
            self.debug = True
        super(DevpiServer, self).__init__(preserve_sys_path=True, **kwargs)

        self.offline = offline
        self.data = data
        self.server_dir = self.workspace / 'server'
        self.client_dir = self.workspace / 'client'
        self.user = user
        self.password = password
        self.index = index

    @property
    def run_cmd(self):
        res = [sys.executable, '-c', 'import sys; from devpi_server.main import main; sys.exit(main())',
                '--serverdir', self.server_dir,
                '--host', self.hostname,
                '--port', str(self.port)
                ]
        if self.offline:
            res.append('--offline-mode')
        if self.debug:
            res.append('--debug')
        return res

    def api(self, *args):
        """ Client API.
        """
        client_args = ['devpi']
        client_args.extend(args)
        client_args.extend(['--clientdir', self.client_dir])
        log.info(' '.join(client_args))
        captured = cStringIO()
        stdout = sys.stdout
        sys.stdout = captured
        try:
            devpi_client(client_args)
            return captured.getvalue()
        finally:
            sys.stdout = stdout


    def pre_setup(self):
        if self.data:
            log.info("Extracting initial server data from {}".format(self.data))
            zipfile.ZipFile(self.data, 'r').extractall(self.server_dir)
        else:
            self.run([sys.executable, '-c', 'import sys; from devpi_server.main import main; sys.exit(main())',
                    '--serverdir', self.server_dir,
                    '--init',
                    ])


    def post_setup(self):
        # Connect to our server
        self.api('use', self.uri)
        # Create and log in initial user
        self.api('user', '-c', self.user, 'password={}'.format(self.password))
        self.api('login', self.user, '--password={}'.format(self.password))
        # Create and use stand-alone index
        self.api('index', '-c', self.index, 'bases=')
        self.api('use', self.index)
        log.info("=" * 60)
        log.info(" Started DevPI server at {}".format(self.uri))
        log.info(" Created initial index at {}/{}".format(self.user, self.index))
        log.info("=" * 60)
