import collections
from distutils import log

from pkg_resources import working_set, ResolutionError
from setuptools import Command

from .base import CommandMixin


class sanity_check(Command, CommandMixin):
    """ Sanity check our virtual environment """
    description = "Sanity check the virtual environment"

    user_options = [
    ]
    boolean_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        errors = collections.defaultdict(list)
        for dist in working_set:
            for req in dist.requires():
                try:
                    working_set.require(str(req))
                except Exception as e:
                    errors[dist].append((req, repr(e)))
        if errors:
            msg = ['']
            for dist in errors:
                msg.append("Package: {}".format(dist))
                for error in errors[dist]:
                    req, err = error
                    msg.append("  Requirement: {}".format(req))
                    msg.append("      {}".format(err))
            raise ResolutionError('\n'.join(msg))
        log.info("All OK")
