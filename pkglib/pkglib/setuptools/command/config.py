from setuptools import Command

from distutils import log

from ... import CONFIG
from ...config import org


class config(Command):
    """ Print PkgLib configuration """
    description = "Print out PkgLib configuration"

    user_options = [
    ]
    boolean_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        log.info("Organisation Config")
        for k in org.ORG_SLOTS:
            log.info("    {0}: {1}".format(k, getattr(CONFIG, k)))
