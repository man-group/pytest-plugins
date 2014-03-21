import os
import stat
import logging
import time

import six.moves.configparser as configparser
from pkglib.six.moves.urllib.error import HTTPError
from pkglib.six.moves.urllib.request import HTTPBasicAuthHandler, Request, build_opener
from pkglib.six.moves.urllib.parse import urlencode

from pkglib import errors


def get_log():
    return logging.getLogger(__name__)


class PyPIRC(object):

    _no_arg = object()

    def __init__(self, filename=None, check_permissions=True):
        self.cfg = self._read_pypirc(filename, check_permissions)
        self._ensure_distutils_section_exists()

    def _read_pypirc(self, filename, check_permissions=True):
        cfg = configparser.ConfigParser()
        if filename is None or not os.path.exists(filename):
            return cfg

        st_mode = os.stat(filename).st_mode
        if check_permissions and st_mode & (stat.S_IRGRP | stat.S_IWGRP |
                                            stat.S_IROTH | stat.S_IWOTH) != 0:
            raise errors.UserError("Invalid `.pypirc` permissions! File must be "
                                   "accessible by the current user only", filename)
        get_log().info("Reading PyPi configuration from: %s" % filename)
        cfg.read(filename)
        return cfg

    def _ensure_distutils_section_exists(self):
        if not self.cfg.has_section("distutils"):
            self.cfg.add_section("distutils")

            if self.cfg.has_section("server-login"):
                # http://wiki.python.org/moin/EnhancedPyPI
                get_log().info("Converting PyPi configuration from legacy "
                               "format")
                self.cfg.set("distutils", 'index-servers', 'server-login')

        if not self.cfg.has_option("distutils", "index-servers"):
            self.cfg.set("distutils", "index-servers", "")

    def _canonical_repository_uri(self, uri):
        return uri.lower().strip().rstrip("/")

    def _get_server_section_by_uri(self, uri, create_if_not_exists=False):
        canonical_uri = self._canonical_repository_uri(uri)
        index_servers = [s for s in self.cfg.get("distutils",
                                                 "index-servers").split()
                         if s.strip()]
        for s in index_servers:
            if not (self.cfg.has_section(s) and
                    self.cfg.has_option(s, "repository")):
                continue

            repository = self.cfg.get(s, "repository")
            section_pypi_uri = self._canonical_repository_uri(repository)
            if section_pypi_uri == canonical_uri:
                return s

        if not create_if_not_exists:
            return None

        while True:
            candidate_section_name = "server_%d" % int(time.time())
            if candidate_section_name not in self.cfg.sections():
                index_servers.append(candidate_section_name)
                self.cfg.add_section(candidate_section_name)
                self.cfg.set(candidate_section_name, "repository", uri)
                self.cfg.set("distutils", "index-servers",
                             "\n".join(index_servers))
                break

        return candidate_section_name

    def _get_server_info(self, uri):
        section_name = self._get_server_section_by_uri(uri)
        return dict(self.cfg.items(section_name)) if section_name else {}

    def _set_server_info(self, uri, item, value):
        section_name = (self._get_server_section_by_uri
                        (uri, create_if_not_exists=True))
        if value != PyPIRC._no_arg:
            self.cfg.set(section_name, item, value if value else "")

    def get_server_uris(self):
        index_servers = set(s for s in
                            self.cfg.get("distutils", "index-servers").split()
                            if s.strip())
        return set((self.cfg.get(s, "repository") for s in index_servers
                    if self.cfg.has_option(s, "repository")))

    def get_server_username(self, uri):
        return self._get_server_info(uri).get("username")

    def get_server_password(self, uri):
        d = self._get_server_info(uri)
        return d.get("password")

    def set_server_username(self, uri, username=_no_arg):
        self._set_server_info(uri, "username", username)

    def set_server_password(self, uri, password=_no_arg):
        self._set_server_info(uri, "password", password)

    def remove_server(self, uri):
        section_name = self._get_server_section_by_uri(uri)
        existed = False
        if section_name:
            existed = self.cfg.remove_section(section_name)
            index_servers = "\n".join((s for s in
                                       self.cfg.get("distutils",
                                                    "index-servers").split()
                                       if s != section_name))
            self.cfg.set("distutils", "index-servers", index_servers)
        return existed

    def validate_credentials(self, uri):
        """Submit a dummy request to PyPi to validate credentials."""
        # If the credentials are valid we expect 400, since the request is
        # invalid, else 401 Unauthorized.
        d = self._get_server_info(uri)
        auth = HTTPBasicAuthHandler()
        auth.add_password('pypi', uri, d.get('username'), d.get('password'))
        request = Request(uri + '?' + urlencode({':action': 'file_upload'}))
        try:
            # Use a fresh opener to ensure we don't fall back to a cached
            # username/password
            result = build_opener(auth).open(request)
            status = result.getcode()
            msg = result.msg
            reason = result.read()
        except HTTPError as ex:
            status = ex.code
            msg = ex.msg
            reason = '' if ex.fp is None else ex.fp.read()

        if not isinstance(msg, str):
            msg = msg.decode('utf-8')

        if reason:
            if not isinstance(reason, str):
                reason = reason.decode('utf-8')
            msg = msg + ': ' + reason

        if status == 400:
            get_log().debug('Validated PyPi credentials with %s', uri)
        elif status == 401:
            raise errors.UserError('Invalid PyPi credentials', uri, msg)
        else:
            raise IOError('Unexpected status from PyPi', uri, status, msg)

    def _save(self, cfg, filename, check_permissions=True):
        get_log().debug("Saving PyPi configuration to: %s" % filename)
        with open(filename, 'wb') as rc_file:
            cfg.write(rc_file)

        if check_permissions:
            os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)

    def save(self, filename, check_permissions=True):
        """
        Saves current configuration to a file.
        """
        self._save(self.cfg, filename, check_permissions)

    def save_in_legacy_format(self, filename, uri=None, check_permissions=True):
        """
        Saves the configuration using `server-login` section.
        """
        configured_uris = self.get_server_uris()
        if not len(configured_uris):
            raise RuntimeError("No repositories are configured")

        if uri:
            if not self._get_server_info(uri):
                raise RuntimeError("Unconfigured repository for URI: %s" % uri)
        else:
            if len(configured_uris) > 1:
                raise RuntimeError("More that one repository configured: "
                                   "please provide URI")

            uri = list(configured_uris)[0]

        config = configparser.RawConfigParser()
        config.add_section('server-login')
        config.set('server-login', 'repository', uri)
        config.set('server-login', 'username', self.get_server_username(uri))
        config.set('server-login', 'password', self.get_server_password(uri))
        self._save(config, filename, check_permissions)
