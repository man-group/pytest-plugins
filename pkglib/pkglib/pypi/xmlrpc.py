"""  PyPi accessor module
"""
import logging
import urllib2
import exceptions
import xmlrpclib
import urlparse

from xml.etree.cElementTree import ElementTree

from pkglib import util
from pkglib.errors import UserError

from base import PyPiAPI


def get_log():
    return logging.getLogger(__name__)


def has_pypi_xmlrpc_interface(uri):
    """
    Detect whether or not the specified server provides the PyPI XML-RPC
    interface.
    """
    url = urlparse.urljoin(uri, '/')
    client = xmlrpclib.ServerProxy(url)
    try:
        client.list_packages()
    # TODO: catch more specific errors
    except Exception:
        return False
    return True


class XMLRPCPyPIAPI(PyPiAPI):
    """ XMLRPC-supported PyPI API object.
        Caching lookup of packages by name for their VCS uris.
    """
    def __init__(self, uri=None, username=None, password=None):
        super(XMLRPCPyPIAPI, self).__init__(uri, username, password)
        uri = self.uri
        if not uri.endswith('/'):
            uri += '/'
        self.proxy = xmlrpclib.ServerProxy(uri)

    def get_package_metadata(self, package, version):
        pkg_info = self.proxy.release_data(package, version)
        return pkg_info

    def get_last_version(self, package, dev=False, strict=False):
        versions = self.get_available_versions(package, dev, strict)
        if not versions:
            return None
        return versions[0]

    def get_available_versions(self, package, dev=False, strict=False):
        """
        Parameters
        ----------
        package: `str`
            Package name
        dev: `bool` or `None`
            If `True`, return only dev versions; if `False`, return only release
            versions; otherwise, return all versions.
        strict: `bool`
            If set, matches dev versions strictly.
            Eg: 0.0.dev OK, 2.33.dev3 -not OK.

        Returns: version strings, sorted with highest version first
        """
        fn = util.is_strict_dev_version if strict else util.is_dev_version

        versions = set()
        for hidden in (False, True):
            for release in self.proxy.package_releases(package, hidden):
                if dev is None or dev == fn(release):
                    versions.add(release)
        
        return sorted(versions, key=util.parse_version, reverse=True)

    def get_vcs_uri(self, pkg):
        """ Return the VCS uri for a given package.
        """
        if pkg not in self._cache:
            self._cache[pkg] = self.get_package_homepage(self.uri, pkg)
        return self._cache[pkg]

    def get_package_homepage(self, uri, pkg):
        """ Use the XML-RPC interface to query release metadata for a given
            package
        """
        for release in self.get_available_versions_rpc(pkg, dev=None):
            release_data = self.proxy.release_data(pkg, release)
            home_page = release_data.get('home_page', '')
            if len(home_page) > 4:
                return home_page

        raise UserError("Can't find repository URL for package %s. "
                        "Has it been registered in PyPi?" % pkg)

    def get_links(self, pkg_name):
        """
        Return the simple page links.
        """
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen('%s/simple/%s' % (self.uri, pkg_name)))
        except (urllib2.HTTPError, exceptions.SyntaxError):
            return None

        return tree.getroot().findall('body/a')
