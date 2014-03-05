import re
import os
from distutils.version import LooseVersion, Version

from six import string_types

from pkglib import CONFIG


RE_DEV_VERSION = re.compile('\.dev\d*$')
DEFAULT_VERSION_SEP = "."


def is_inhouse_package(name):
    """
    True if this package is an in-house package
    """
    for prefix in CONFIG.namespaces:
        if name.startswith(prefix + CONFIG.namespace_separator):
            return True
    return False


def is_dev_version(version):
    """
    True if this version is a dev version
    """
    return RE_DEV_VERSION.search(version)


def is_strict_dev_version(version):
    """
    True if this version is a dev version, and the numeric component matches
    our static build number.
    """
    # This one matches only versions that also match our dev build version
    strict_re = re.compile('^{}\.dev\d*$'
                           .format(CONFIG.dev_build_number.replace('.', '\.')))
    return strict_re.search(version)


def get_build_egg_dir():
    """
    Returns the path to the directory where tests_require dependencies
    are installed into
    """
    return os.path.join(os.getcwd(), '.build-eggs')


def maybe_add_simple_index(url):
    """Checks if the server URL should have a /simple on the end of it.
       This is to get around the brain-dead difference between upload/register
       and easy_install URLs.
    """
    if not url.endswith('/simple') and not url.endswith('/simple/'):
        url += '/simple'
    return url


def get_namespace_packages(name):
    """
    Returns all the namespace packages for a given package name
    >>> get_namespace_packages('foo')
    []
    >>> get_namespace_packages('foo.bar')
    ['foo']
    >>> get_namespace_packages('foo.bar.baz')
    ['foo', 'foo.bar']
    """
    parts = name.split(CONFIG.namespace_separator)
    if len(parts) < 2:
        return []
    res = []
    for i in range(len(parts) - 1):
        res.append('.'.join(parts[:i + 1]))
    return res


def parse_version(version):
    """ Safely parses string, iterable or `distutils.version.Version` and
        returns as `distutils.version.LooseVersion`"""
    if not isinstance(version, Version):
        version = LooseVersion(version if isinstance(version, string_types)
                               else ".".join(str(p) for p in version))
    return version


def short_version(version, max_parts=None, prefix=None, suffix=None,
                  separator=DEFAULT_VERSION_SEP):
    parts = parse_version(version).version[:max_parts]
    return "%s%s%s" % (prefix if prefix else "",
                       separator.join(str(p) for p in parts),
                       suffix if suffix else "")


def flatten(*args):
    """ Flatten iterable arguments into a single list
    """
    output = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            output.extend(flatten(*list(arg)))
        else:
            output.append(arg)
    return output
