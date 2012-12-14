from setuptools.dist import Distribution

from pkglib.setuptools.command.test import test


def test_namespace_dirs_single():
    dist = Distribution(dict(packages=['acme'], namespace_packages=['acme']))
    cmd = test(dist)
    assert cmd.get_namespace_dirs() == set(['acme'])


def test_namespace_dirs_nested():
    dist = Distribution(dict(packages=['acme.foo.bar'],
                             namespace_packages=['acme', 'acme.foo', 'acme.foo.bar']))
    cmd = test(dist)
    assert cmd.get_namespace_dirs() == set(['acme'])


def test_namespace_dirs_many():
    dist = Distribution(dict(packages=['acme.foo.bar', 'blackmesa.blah'],
                             namespace_packages=['acme', 'acme.foo', 'acme.foo.bar', 'blackmesa', 'blackmesa.blah']))
    cmd = test(dist)
    assert cmd.get_namespace_dirs() == set(['acme', 'blackmesa'])
