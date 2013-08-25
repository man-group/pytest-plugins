"""  PyPi accessor module for the ClueReleaseManager
"""
import re
import logging
import urllib2
import exceptions

from xml.etree.cElementTree import ElementTree

from pkglib.errors import UserError

from base import PyPiAPI


def get_log():
    return logging.getLogger(__name__)

RE_NAMESPACE = re.compile('^{([^}]+)}.*$')


class CluePyPIAPI(PyPiAPI):
    """ ClueReleaseManager PyPI API object.
        Caching lookup of packages by name for their VCS uris.
    """
    def _pkg_home(self, pkg):
        """ Return a package's homepage
        """
        return '/'.join([self.uri, 'd', pkg])

    def _get_namespace(self, tree):
        ns = RE_NAMESPACE.match(tree.getroot().tag)
        if ns:
            return "{%s}" % ns.group(1)
        else:
            return ''

    def scrape_pkg_uri(self, uri, pkg):
        """
        Scrape package metadata from PyPi when it's running
        as the Clue Release Manager.

        Parameters
        ----------
        uri : `str`
            URI to page containing package's homepage
        pkg : `str`
            Package name
        """
        # Example entry:
        #<div class="distro-block distro-metadata">
        #  <h4>Metadata</h4>
        #  <dl>
        #    <dt>Distro Index Owner:</dt>
        #    <dd>acmepypi</dd>
        #    <dt>Home Page:</dt>
        #    <dd><a href="http://mysvn/acme.helloworld">
        #           http://mysvn/acme.helloworld</a></dd>
        #  </dl>
        #</div>
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen(uri))
        except urllib2.HTTPError, e:
            raise UserError("Can't find repository URL for package %s (%s). "
                            "Has it been registered in PyPi?" % (pkg, e))
        ns = self._get_namespace(tree)

        # Grr py2.6 version of etree doesn't support xpath
        #metadata = tree.find('//div[@class="distro-block distro-metadata"]')
        for div in tree.getroot().find(ns + 'body').findall(ns + 'div'):
            if 'distro-metadata' in div.attrib['class']:
                is_next = False
                for item in div.getiterator('*'):
                    if item.tag == ns + 'dt' and item.text == 'Home Page:':
                        is_next = True
                        continue
                    if is_next and item.tag == ns + 'a':
                        return item.attrib['href']
                break
        raise UserError("Can't find repository URL for package %s. "
                        "Has it been registered in PyPi?" % pkg)

    def get_vcs_uri(self, pkg):
        """ Return the VCS uri for a given package.
        """
        # Don't use _cache.get because we always evaluate the second arg.
        if pkg not in self._cache:
            self._cache[pkg] = self.scrape_pkg_uri(self._pkg_home(pkg), pkg)
        return self._cache[pkg]

    def get_links(self, pkg_name):
        """ Return the simple page links
        """
        tree = ElementTree()
        try:
            tree.parse(urllib2.urlopen('%s/simple/%s' % (self.uri, pkg_name)))
        except (urllib2.HTTPError, exceptions.SyntaxError):
            return None

        ns = self._get_namespace(tree)
        return tree.getroot().findall(ns + 'body/ul/li/a')
