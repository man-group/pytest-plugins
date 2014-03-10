import pytest

import pkg_resources
from zc.buildout.easy_install import _final_version
from pkglib.setuptools.buildout import Installer

pytest_plugins = ['pkglib_testing.pytest.parametrize_ids']


class Dist(object):
    def __init__(self, version, identifier=None):
        self.version = version
        self.identifier = identifier    # used to differentiate dists with the
                                        # same version
        self.parsed_version = pkg_resources.parse_version(version)

    def __repr__(self):
        if self.identifier:
            return self.version + "-" + self.identifier
        return self.version


@pytest.mark.parametrize(("d1", "d2", "prefer_final", "expected"), [
    (Dist("2.0.dev1"), Dist("1.0.dev1"), True, "2.0.dev1"),
    (Dist("2.0.dev1"), Dist("1.0.dev1"), False, "2.0.dev1"),
    (Dist("2.0.dev1"), Dist("1.0"), True, "1.0"),
    (Dist("2.0.dev1"), Dist("1.0"), False, "2.0.dev1"),
    (Dist("2.0"), Dist("1.0.dev1"), True, "2.0"),
    (Dist("2.0"), Dist("1.0.dev1"), False, "1.0.dev1"),
    (Dist("2.0"), Dist("1.0"), True, "2.0"),
    (Dist("2.0"), Dist("1.0"), False, "2.0"),
])
def test_choose_between_different_versions(d1, d2, prefer_final, expected):
    """ Tests choosing between two different versions of a
        package in the installer
    """
    installer = Installer()
    if prefer_final:
        comparitor = _final_version
    else:
        comparitor = installer.is_dev_version

    choice = installer.choose_between(d1, d2, comparitor)
    assert repr(choice) == expected

    # Ordering shouldn't matter
    choice = installer.choose_between(d2, d1, comparitor)
    assert repr(choice) == expected


@pytest.mark.parametrize(("d1", "d2", "prefer_final", "expected"), [
    (Dist("2.0.dev1", 'a'), Dist("2.0.dev1", 'b'), True, "2.0.dev1-a"),
    (Dist("2.0.dev1", 'a'), Dist("2.0.dev1", 'b'), False, "2.0.dev1-a"),
    (Dist("2.0", 'a'), Dist("2.0", 'b'), True, "2.0-a"),
    (Dist("2.0", 'a'), Dist("2.0", 'b'), False, "2.0-a"),
])
def test_choose_between_same_versions(d1, d2, prefer_final, expected):
    """ Tests choosing between two distributions with the same
        version in the installer.
    """
    installer = Installer()
    if prefer_final:
        comparitor = _final_version
    else:
        comparitor = installer.is_dev_version

    # Ordering is important here - it should choose the first one
    choice = installer.choose_between(d1, d2, comparitor)
    assert repr(choice) == expected


