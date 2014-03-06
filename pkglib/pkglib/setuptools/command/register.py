from setuptools.command.register import register as _register
from distutils import log

from six.moves import urlparse, HTTPPasswordMgr  # @UnresolvedImport

from .base import CommandMixin


class register(_register, CommandMixin):
    """ Wrapper around register command to raise correct return codes
        to the system.
    """
    __doc__ = _register.__doc__  # @ReservedAssignment
    _ok_status_codes = [200]

    def run(self):
        self._run(_register, 'register')

    def send_metadata(self):
        """ Send the metadata to the package index server.

            1. figure who the user is, and then
            2. send the data as a Basic auth'ed POST.

            First we try to read the username/password from $HOME/.pypirc,
            which is a ConfigParser-formatted file with a section
            [distutils] containing username and password entries (both
            in clear text) e.g.::

                [distutils]
                index-servers =
                    pypi

                [pypi]
                username: fred
                password: sekrit

            Otherwise, to figure who the user is, we offer the user three
            choices:

            1. use existing login,
            2. prompt to specify and alternate username

            You will always be prompted for a password unless it has already
            been set in the .pypirc file. There will be an option to save
            your credentials in a file to speed up future access to AHL PyPI.
        """
        username, password = self.request_credentials(self.repository)

        # set up the authentication
        auth = HTTPPasswordMgr()
        host = urlparse(self.repository)[1]
        auth.add_password(self.realm, host, username, password)

        # send the info to the server and report the result
        code, result = self.post_to_server(self.build_post_data('submit'), auth)
        self.announce('Server response (%s): %s' % (code, result), log.INFO)

        # possibly save the login
        if code == 200:
            self.store_credentials(username, password)
