import getpass
import os
import textwrap
from pkglib.six.moves import configparser, input  # @UnresolvedImport

from distutils.config import PyPIRCCommand as _PyPIRCCommand
from distutils import log

from pkglib import CONFIG
from pkglib.pypi import xmlrpc


class PyPIRCCommand(_PyPIRCCommand):
    # XXX This does NOT get called for develop or install. Find a way to wire it in.

    DEFAULT_REPOSITORY = CONFIG.pypi_url

    def _get_rc_file(self):
        """Returns rc file path."""
        return os.path.join(os.path.expanduser('~'), '.pypirc')

    # TODO: re-factor to use pkglib.pypi.PyPIRC
    def _read_pypirc(self):
        """Reads the ``.pypirc`` file."""
        rc = self._get_rc_file()
        if os.path.exists(rc):
            self.announce('Using PyPI login from %s' % rc)
            repository = self.repository or self.DEFAULT_REPOSITORY
            config = configparser.ConfigParser()
            config.read(rc)

            sections = config.sections()
            if 'distutils' in sections:
                # let's get the list of servers
                index_servers = config.get('distutils', 'index-servers')
                _servers = [server.strip() for server in
                            index_servers.split('\n')
                            if server.strip() != '']
                if _servers == []:
                    # nothing set, let's try to get the default pypi
                    if 'pypi' in sections:
                        _servers = ['pypi']
                    else:
                        # the file is not properly defined, returning
                        # an empty dict
                        return {}

                for server in _servers:
                    current = {'server': server}
                    current['username'] = config.get(server, 'username')

                    # optional params
                    for key, default in (('repository',
                                          self.DEFAULT_REPOSITORY),
                                         ('realm', self.DEFAULT_REALM),
                                         ('password', None)):
                        if config.has_option(server, key):
                            current[key] = config.get(server, key)
                        else:
                            current[key] = default

                    #   THIS IS REALLY UGLY! New style config is very
                    # likely to fall over if you get your URLs wrong i.e.
                    # '/' on the end of your URL or not ...
                    if ((current['server'] == repository or
                         current['repository'] == repository)):
                        return current

            elif 'server-login' in sections:
                # old format
                server = 'server-login'
                if config.has_option(server, 'repository'):
                    repository = config.get(server, 'repository')
                else:
                    repository = self.DEFAULT_REPOSITORY

                try:
                    # later versions of distutils initialise password to ''
                    if hasattr(self.distribution, 'password'
                               ) and self.distribution.password:
                        #   Re-use stowed password if it has already been set.
                        password = self.distribution.password
                    else:
                        #   Use password from config file.
                        password = config.get(server, 'password')
                except configparser.NoOptionError:
                    #   Prompt for password.
                    password = getpass.getpass('Password: ')

                #   Stow the password for use with other chained commands.
                self.distribution.password = password

                return {
                    'username': config.get(server, 'username'),
                    'password': password,
                    'repository': repository,
                    'server': server,
                    'realm': self.DEFAULT_REALM,
                }
        return {}

    def request_credentials(self, repository):
        """Prompt user for credentials if they are partial or missing."""
        if hasattr(self.distribution, 'username'
                   ) and hasattr(self.distribution, 'password'):
            #   Using cached credentials from a previous command.
            return self.distribution.username, self.distribution.password

        username = ''
        password = ''

        config = self._read_pypirc()
        if config:
            # User can specify a different username and password.
            self.repository = config['repository']
            # config file setting overrides default setting
            repository = self.repository
            self.realm = config['realm']
            username = config.get('username', '')
            password = config.get('password', '')

        if not xmlrpc.has_pypi_xmlrpc_interface(repository):
            #   Clue specific behaviour.
            self.announce('using default credentials for cluereleasemanager',
                          log.INFO)
            username = CONFIG.pypi_default_username
            password = CONFIG.pypi_default_password

            return username, password
        # get the username and password
        while not username:
            default_user = getpass.getuser()
            username = input('Username (default: %s): ' % default_user)
            if not username:
                username = default_user
            self.username = username

        while not password:
            password = getpass.getpass('Password: ')

        return username, password

    def _store_pypirc(self, username, _password):
        """Creates a default ``.pypirc`` file."""
        # unlike distutils, this patched version *does not* store the password
        # in the output file !!!

        pypirc_template = textwrap.dedent("""\
        [distutils]
        index-servers =
            localpypi

        [localpypi]
        repository=%(repository)s
        username=%(username)s
        """)

        rc = self._get_rc_file()
        f = open(rc, 'w')
        try:
            f.write(pypirc_template % {'username': username,
                                       'repository': self.repository})
        finally:
            f.close()
        try:
            os.chmod(rc, 0o600)
        except OSError:
            # should do something better here
            pass

    def store_credentials(self, username, password):
        """Store user credentials."""
        #   Cache username and password in distribution object so they can
        #   be shared between commands.
        self.distribution.username = username
        self.distribution.password = password
