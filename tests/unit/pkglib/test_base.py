from setuptools.dist import Distribution
from setuptools import Command
from mock import Mock

from pkglib.setuptools.command import base


class TestCmd(Command, base.CommandMixin):
    user_options = [('foo', None, 'xxx'), ('bar', None, 'xxx')]

    def initialize_options(self):
        self.foo = 1
        self.bar = 2

    def finalize_options(self):
        pass


def get_cmd():
    dist = Distribution({'name': 'acme.foo'})
    cmd = TestCmd(dist)
    return cmd


def test_get_option_list():
    cmd = get_cmd()
    assert cmd.get_option_list() == [('foo', 1), ('bar', 2)]
