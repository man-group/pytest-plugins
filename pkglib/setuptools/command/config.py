from setuptools import Command

from distutils import log


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
        import pkglib
        from pkglib.config import ORG_SLOTS, TEST_SLOTS
        log.info("Organisation Config")
        for k in ORG_SLOTS:
            log.info("    {0}: {1}".format(k, getattr(pkglib.CONFIG, k)))
        log.info("Testing Config")
        for k in TEST_SLOTS:
            log.info("    {0}: {1}".format(k, getattr(pkglib.CONFIG, k)))

