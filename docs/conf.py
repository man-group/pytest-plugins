""" Sphinx configuration is sourced from within pkgutils
"""
import os
import sys
from pkglib.sphinx.conf import *
if os.environ.get('READTHEDOCS', None) == 'True': 
    # Some rather nasty hackery to support executing conf.py under readthedocs
    os.chdir('..')
    # This to trigger the autodoc
    sys.argv = ['setup.py', 'build_sphinx', '--no-sphinx']
    try:
        execfile('setup.py', locals(), globals())
    except SystemExit:
        pass
    # Read the metadata from setup.cfg
    metadata = config.parse_pkg_metadata(config.get_pkg_cfg_parser())
    project = metadata['name']
    version = metadata['version']
    os.chdir('docs')
