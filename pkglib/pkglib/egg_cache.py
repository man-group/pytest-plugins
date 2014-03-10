from __future__ import absolute_import
import os
from distutils import log

from setuptools.package_index import PackageIndex
from pkg_resources import Distribution

from pkglib import CONFIG

__all__ = ['get_egg_cache_paths', 'EggCacheAwarePackageIndex', 'is_from_egg_cache', 'egg_cache_path_from_url']


""" A user may optionally set CONFIG.installer_search_path to point to a local egg cache
of release version eggs and CONFIG.installer_dev_search_path to point to a similar cache of
dev version eggs. The pypi server is used to discover available eggs but a download can be
avoided if the egg is available in either egg cache. To save on disc space and further speed
things up we link to eggs in the cache however because we produce so many dev eggs each
day and we can't keep them all the dev egg cache is cleaned on a regular basis. As a result
it is not safe to link to eggs in the dev egg cache so they must be copied.

In Jenkins we don't set CONFIG.installer_dev_search_path but instead put both paths in
CONFIG.installer_search_path. This speeds up builds as all the eggs can be linked and not copied.
This works because enviroments in Jenkins do not usually last longer than the lifetime of
eggs in the dev egg cache.
"""


def _valid_paths(paths):
    res = []
    for path in paths:
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            log.warn("Invalid egg cache directory: %s", path)
            continue
        res.append(path)
    return res


def get_egg_cache_paths():
    """ Returns a list of the paths to any egg caches configured. This reads the
    CONFIG.installer_search_path variable. Eggs in the cache don't need to be
    downloaded from pypi and can be linked to."""
    return _valid_paths(CONFIG.installer_search_path)


def get_dev_egg_cache_paths():
    """ Returns a list of the paths to any dev egg caches configured. This reads the
    CONFIG.installer_dev_search_path enviroment variable. Eggs in the dev cache don't need
    to be downloaded from pypi but get deleted regularly so can't be linked to so must
    be copied into the user's enviroment"""
    return _valid_paths(CONFIG.installer_dev_search_path)


def is_from_egg_cache(path):
    """ Tells you if the given path is in the egg cache. This only considers the egg cache
    and not the dev egg cache. This function is used to decide if an egg can be linked to
    rather than copying it."""
    return any(os.path.dirname(path).startswith(egg_cache_path)
               for egg_cache_path in get_egg_cache_paths())


def egg_cache_path_from_url(url, filename):
    """ Given the url to an egg in pypi returns to the path to the egg in the egg cache or the
    dev egg cache. If the egg isn't in either cache then this returns None"""
    clean_url = url
    if '#' in clean_url:
        clean_url, _ = clean_url.split('#', 1)

    if clean_url.endswith('.egg'):
        dist = Distribution.from_location(clean_url, os.path.basename(clean_url))

        for root in get_egg_cache_paths() + get_dev_egg_cache_paths():
            initials = "".join(map(lambda x: x[0], dist.project_name.split(".")[:2])).lower()
            pth = str(os.path.join(root, initials, dist.egg_name() + ".egg"))
            if os.path.exists(pth):
                return pth
    return None


class EggCacheAwarePackageIndex(PackageIndex):
    """Replaces PackageIndex for easy_install and causes it to avoid downloading eggs when they
    are available in the egg cache (or the dev egg cache)."""
    def _attempt_download(self, url, filename):
        res = egg_cache_path_from_url(url, filename)
        if res is None:
            res = super(EggCacheAwarePackageIndex, self)._attempt_download(url, filename)
        return res
