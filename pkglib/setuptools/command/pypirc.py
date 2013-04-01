import os
import ConfigParser
from distutils.config import PyPIRCCommand as _PyPIRCCommand
from distutils import log
import getpass
import textwrap

from pkglib import CONFIG


class PyPIRCCommand(_PyPIRCCommand):
    # XXX XXX: This does NOT get called for develop or install. Fix this.
    DEFAULT_REPOSITORY = CONFIG.pypi_url

    def _get_rc_file(self):
        """Returns rc file path."""
        return os.path.join(os.path.expanduser('~'), '.pypirc')

    def _read_pypirc(self):
        """Reads the ``.pypirc`` file."""
        rc = self._get_rc_file()
        if os.path.exists(rc):
            self.announce('Using PyPI login from %s' % rc)
            repository = self.repository or self.DEFAULT_REPOSITORY
            config = ConfigParser.ConfigParser()
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
                    for key, default in (('repository', self.DEFAULT_REPOSITORY),
                                         ('realm', self.DEFAULT_REALM),
                                         ('password', None)):
                        if config.has_option(server, key):
                            current[key] = config.get(server, key)
                        else:
                            current[key] = default

                    #   THIS IS REALLY UGLY! New style config is very likely to fall over if you get
                    #   your URLs wrong i.e. '/' on the end of your URL or not ...
                    if (current['server'] == repository or current['repository'] == repository):
                        #current['repository'] = self.maybe_add_simple_index(current['repository'])
                        return current

            elif 'server-login' in sections:
                # old format
                server = 'server-login'
                if config.has_option(server, 'repository'):
                    #repository = self.maybe_add_simple_index(config.get(server, 'repository'))
                    repository = config.get(server, 'repository')
                else:
                    #repository = self.maybe_add_simple_index(self.DEFAULT_REPOSITORY)
                    repository = self.DEFAULT_REPOSITORY

                try:
                    # later versions of distutils initialise password to ''
                    if hasattr(self.distribution, 'password') and self.distribution.password:
                        #   Re-use stowed password if it has already been set.
                        password = self.distribution.password
                    else:
                        #   Use password from config file.
                        password = config.get(server, 'password')
                except ConfigParser.NoOptionError:
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
        if hasattr(self.distribution, 'username') and hasattr(self.distribution, 'password'):
            #   Using cached credentials from a previous command.
            return self.distribution.username, self.distribution.password

        username = ''
        password = ''

        config = self._read_pypirc()
        if config:
            #   User can specify a different username and password.
            self.repository = config['repository']
            repository = self.repository    #   Config file setting overrides default setting.
            self.realm = config['realm']
            username = config.get('username', '')
            password = config.get('password', '')

        # get the username and password
        while not username:
            default_user = getpass.getuser()
            username = raw_input('Username (default: %s): ' % default_user)
            if not username:
                username = default_user
            self.username = username

        while not password:
            password = getpass.getpass('Password: ')

        return username, password

    def _store_pypirc(self, username, password):
        """Creates a default ``.pypirc`` file."""
        # !!! unlike distutils, this patched version *does not* store the password in the output file !!!
        old_style_pypirc_template = textwrap.dedent("""\
        [server-login]
        repository=%(repository)s
        username=%(username)s
        """)

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
            f.write(pypirc_template % {'username': username, 'repository': self.repository })
        finally:
            f.close()
        try:
            os.chmod(rc, 0600)
        except OSError:
            # should do something better here
            pass

    def store_credentials(self, username, password):
        """Store user credentials."""
#   Supporting this features is more trouble than its worth
#DISABLED:        if not self.has_config:
#DISABLED:            self.announce(('I can store your PyPI login so future submissions will be faster.'), log.INFO)
#DISABLED:            self.announce('(the login will be stored in %s)' % self._get_rc_file(), log.INFO)
#DISABLED:            choice = 'X'
#DISABLED:            while choice.lower() not in 'yn':
#DISABLED:                choice = raw_input('Save your login (y/n)?')
#DISABLED:            if choice.lower() == 'y':
#DISABLED:                self._store_pypirc(username, password)

        #   Cache username and password in distribution object so they can
        #   be shared between commands.
        self.distribution.username = username
        self.distribution.password = password
