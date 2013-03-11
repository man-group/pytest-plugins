import pytest

import pkg_resources
from zc.buildout.easy_install import _final_version
from pkglib.setuptools.buildout import Installer

pytest_plugins = ['pkglib.testing.pytest.parametrize_ids']


class Dist(object):
    def __init__(self, version):
        self.version = version
        self.parsed_version = pkg_resources.parse_version(version)

    def __repr__(self):
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
def test_choose_between(d1, d2, prefer_final, expected):
    """ Tests choosing between two versions in the installer
    """
    installer = Installer()
    if prefer_final:
        comparitor = _final_version
    else:
        comparitor = installer.is_dev_version

    choice = installer.choose_between(d1, d2, comparitor)
    assert str(choice.version) == expected

    # Ordering shouldn't matter
    choice = installer.choose_between(d2, d1, comparitor)
    assert str(choice.version) == expected

