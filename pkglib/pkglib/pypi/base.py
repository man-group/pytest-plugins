"""  PyPi accessor module
"""
import sys
import logging
import urllib2


from pkg_resources import Distribution, parse_version

from pkglib import CONFIG, util
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

    def get_egg_distribution_links(self, package, version=None,
                                   py_version=sys.version_info,
                                   dev=False, strict=False):
        """
        Return links to available egg distributions.

        Parameters
        ----------
        package : `str`
            name of the package
        version : `str` or `bool`
            version of the package. Optional, if not provided links for all
            available versions of the package will be returned.
        py_version : `str` or `distutils.version.Version`
            target Python version for distributions. Only those distributions
            which are compatible with the version of Python will be returned.
            Defaults to the Python version of the current interpreter. If
            None is provided will return distributions for all Python
            platforms.
        dev: `bool`
            If set, will only return dev versions. Otherwise, return
            only released versions.
        strict: `bool`
            If set, matches dev versions strictly.
            Eg: 0.0.dev OK, 2.33.dev3 -not OK.

        Returns
        -------
        dists : `dict`
            a map of `str`->`pkg_resources.Distribution`
            (distribution URL -> distribution object)
        """

        fn = ((util.is_strict_dev_version if strict else util.is_dev_version) if dev
              else (lambda v: not util.is_dev_version(v)))
        py_version = py_version and util.short_version(py_version, max_parts=2)
        dists = {}

        for l in self.get_links(package):
            if not l.endswith(".egg"):
                continue

            d = Distribution.from_filename(l.rsplit("/", 1)[-1])

            if py_version and d.py_version != py_version:
                continue

            if not fn(d.version):
                continue

            if version and d.version != version:
                continue

            dists[l] = d

        return dists

    def get_available_versions(self, package, py_version=sys.version_info,
                               dev=False, strict=False):
        links = self.get_egg_distribution_links(package, py_version=py_version,
                                                dev=dev, strict=strict)
        return sorted((d.version for d in links.values()),
                      key=parse_version, reverse=True)

    def get_last_version(self, package, dev=False, strict=False):
        versions = self.get_available_versions(package, dev=dev, strict=strict)
        return versions[0] if versions else None

