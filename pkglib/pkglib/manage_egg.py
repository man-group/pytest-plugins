import logging
from zipfile import ZipFile
from contextlib import closing

from six.moves import cStringIO, configparser   # @UnresolvedImport

from distutils.dist import DistributionMetadata

_ATTRIBUTE_MAP = {"url": "home_page",
                  "long_description": "description",
                  "description": "summary",
                  "platforms": "platform"}


def get_log():
    return logging.getLogger(__name__)


def get_egg_metadata(egg_file):
    """
    Reads and returns meta data of the given egg file, converted
    to `distutils.dist.DistributionMetadata`.
    """
    # late import to prevent setup.py from failing during bootstrapping
    from pkgtools.pkg import Egg

    def _get_metadata_value(n, d):
        n = n.lower().replace("-", "_")
        for k, nk in ((k, k.lower().replace("-", "_")) for k in d.keys()):
            if nk.lower() == n:
                return d[k]

    bdist = Egg(egg_file)
    metadata = DistributionMetadata()
    for f in DistributionMetadata._METHOD_BASENAMES:
        val = _get_metadata_value(_ATTRIBUTE_MAP.get(f, f), bdist.pkg_info)
        if val:
            setattr(metadata, f, val)

    return metadata


def get_dev_externals(egg_file):
    with closing(ZipFile(egg_file, "r")) as egg:
        try:
            externals = egg.read("EGG-INFO/externals.txt")
        except KeyError:
            return []

    cfg = configparser.RawConfigParser()
    cfg.readfp(cStringIO(externals))
    return (cfg.get("dev", "files").strip().split("\n")
            if cfg.has_option("dev", "files") else [])


def has_dev_externals(egg_file):
    return len(get_dev_externals(egg_file)) > 0
