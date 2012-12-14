from setuptools import Command

from base import CommandMixin


class release_externals(Command, CommandMixin):
    """ Hook for packages to do any externally-managed releases """
    description = "External release hook"

    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        pass
