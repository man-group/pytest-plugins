"""  PyPi accessor module
"""
import os
import re
import logging
import urllib2

from pkglib import CONFIG
from mirror import EggMirrorMixin


def get_log():
    return logging.getLogger(__name__)


class PyPiAPI(EggMirrorMixin):
    """ PyPI API object.
        Caching lookup of packages by name for their VCS uris, with
        other methods for managing PyPI Servers.
    """
    def __init__(self, uri=None, username=None, password=None):
        self._cache = {}
        if not uri:
            uri = CONFIG.pypi_url
        self.uri = uri
        if username:
            # XXX I don't think this actually works, had to turn on
            # anonymous access to get the tests passing. urllib2 really
            # does suck a bit.
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(None, uri, username, password)
            urllib2.install_opener(urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(password_manager)))

        self.log = logging.getLogger('pkglib.pypi')
        self.log.debug('Using PyPI: %s' % self.uri)

    def resolve_dashed_name(self, pkg):
        """
        This gets around the stupid bloody problem with distutils converting
        all underscores to dashes in package names, and some third party
        packages being uploaded to PyPi with underscores regardless - most
        notably cx_Oracle.

        Eg::

            $ easy_install cx_Oracle
            $ pip freeze
            > cx-Oracle==5.0.3
            $ easy_install cx-Oracle
            > Requirement already satisfied: cx-Oracle==5.0.3
            $ pip uninstall cx-Oracle
            $ easy_install cx-Oracle
            > Can't satisfy requirement: cx-Oracle
            $ eat flaming death
        """
        if not '-' in pkg:
            return pkg

        if self.get_links(pkg):
            get_log().debug("Found pypi links for package %s" % pkg)
            return pkg

        underscores = pkg.replace('-', '_')
        if self.get_links(underscores):
            get_log().debug("Found pypi links for package %s" % underscores)
            return underscores

        get_log().warn("Can't find any repository links for package %s." % pkg)
        return pkg
