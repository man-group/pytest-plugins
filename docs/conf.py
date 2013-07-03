""" Sphinx configuration is sourced from within pkgutils
"""
import os
import sys
from pkglib.sphinx.conf import *
if os.environ.get('READTHEDOCS', None) == 'True': 
    os.chdir('..')
    print os.getcwd()
    sys.argv = ['setup.py', 'build_sphinx']
    execfile('setup.py')

    
