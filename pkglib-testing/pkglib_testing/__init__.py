"""
PkgLib Testing Library
===================

This library contains useful helpers for writing unit and acceptance tests.
"""

# Many of the features here require pkglib configuration, we'll  parse this on
# import for simplicity's sake.
from pkglib import config

config.setup_org_config()
