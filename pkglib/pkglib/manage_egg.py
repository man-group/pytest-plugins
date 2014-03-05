import logging

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