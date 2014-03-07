# #!/bin/env python
from pkglib.setuptools.command import easy_install
easy_install.easy_install.pkglib_bootstrap = True

from setuptools import Distribution

from pkglib.setuptools import dist, setup


def fetch_build_eggs(requires, dist):
    return Distribution.fetch_build_eggs(dist, requires)

dist.fetch_build_eggs = fetch_build_eggs

if __name__ == '__main__':
    setup()
