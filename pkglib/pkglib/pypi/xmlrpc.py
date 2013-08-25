"""  PyPi accessor module
"""
import logging
import urllib2
import exceptions
import xmlrpclib
import urlparse

from xml.etree.cElementTree import ElementTree

from pkglib.errors import UserError
from pkglib.manage import PackageVersion, is_dev_version, is_strict_dev_version

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
        dev: `bool`
            If set, will only return dev versions. Otherwise, return
            only released versions.
        strict: `bool`
            If set, matches dev versions strictly.
            Eg: 0.0.dev OK, 2.33.dev3 -not OK.
        """
        versions = set(self.proxy.package_releases(package) +
                       self.proxy.package_releases(package, True))
        if dev:
            fn = is_dev_version
            if strict:
                fn = is_strict_dev_version
            versions = [version for version in versions
                        if fn(version)]
        else:
            versions = [version for version in versions
                        if not is_dev_version(version)]

        # Sort versions with most recent version at index 0.
        versions = [PackageVersion(v) for v in versions]
        versions.sort(reverse=True)
        versions = [str(v) for v in versions]
        return versions

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
        # add trailing slash if it wasn't specified.
        url = urlparse.urljoin(uri, '/')
        client = xmlrpclib.ServerProxy(url)
        releases = client.package_releases(pkg)
        releases.extend(client.package_releases(pkg, True))
        # True means "hidden releases"

        #TODO: investigate ordering of release versions so we always use
        #      release
        #TODO: data from the most recent one.
        releases.sort()
        for release in releases[::-1]:  # walk backward through releases
            release_data = client.release_data(pkg, release)
            home_page = release_data.get('home_page', '')
            if len(home_page) > 4:
                return home_page

        raise UserError("Can't find repository URL for package %s. "
                        "Has it been registered in PyPI?" % pkg)

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
