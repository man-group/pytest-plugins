from pkglib.six.moves import configparser, cStringIO  # @UnresolvedImport

import pytest

from pkglib.config import parse


def parse_cfg(setup_cfg):
    parser = configparser.ConfigParser()
    parser.readfp(cStringIO(setup_cfg))
    return parser


def test_parse_setup_cfg_install_requires():
    setup_cfg = """
[metadata]
name = test1
install_requires =
    foo
    bla ==  1.2,   <3
"""
    metadata = parse.parse_pkg_metadata(parse_cfg(setup_cfg))
    assert metadata['name'] == "test1"
    assert metadata['extras_require'] == {}
    assert metadata['install_requires'] == ["foo", "bla ==  1.2,   <3"]


def test_parse_setup_cfg_extras_require():
    setup_cfg = """
[metadata]
name = test2
install_requires =
    foo
extras_require =
    Foo : Bla
    Ivan : Kremlin[Mausoleum, Lenin]==1.0, Putin
"""
    metadata = parse.parse_pkg_metadata(parse_cfg(setup_cfg))
    assert metadata["name"] == "test2"
    expected = {"Foo": ["Bla"],
                "Ivan": ["Kremlin[Mausoleum, Lenin]==1.0", "Putin"]}
    assert metadata["extras_require"] == expected


def test_rejects_illegal_characters_in_package_name():
    setup_cfg = """
[metadata]
name = test_4
"""
    with pytest.raises(RuntimeError) as exc:
        parse.parse_pkg_metadata(parse_cfg(setup_cfg), strict=True)
    assert str(exc.value) == ("Package name 'test_4' contains illegal "
                              "character(s); consider changing to 'test-4'")


def test_rejects_illegal_characters_in_requires():
    setup_cfg = """
[metadata]
name = test4
install_requires =
    foo_bar
"""
    with pytest.raises(RuntimeError) as exc:
        parse.parse_pkg_metadata(parse_cfg(setup_cfg), strict=True)
    assert str(exc.value) == ("Invalid name 'foo_bar' in requirement 'foo_bar' "
                              "for 'install_requires' of 'test4'; "
                              "consider changing to 'foo-bar'")


def test_parse_setup_cfg_entry_points():
    setup_cfg = """
[entry_points]
acme.foo =
    bar=baz:qux
console_scripts =
    one=two:three

[metadata]
name = test1
console_scripts =
    alpha=beta:gamma
"""
    metadata = parse.parse_pkg_metadata(parse_cfg(setup_cfg))
    assert metadata['entry_points'] == {'acme.foo': ['bar=baz:qux'],
                                        'console_scripts': ['one=two:three',
                                                            'alpha=beta:gamma',
                                                            ],
                                        }
