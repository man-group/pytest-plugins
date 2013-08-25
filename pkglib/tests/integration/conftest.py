'''
Created on 2 Apr 2012

@author: eeaston
'''
import sys
import subprocess

from pkg_resources import working_set

from pkglib_testing.util import chdir


def pytest_configure(config):
    """
    Here we ensure there's a recent bdist_egg available for all our integration tests
    """
    if sys.argv == ['-c']:
        # This is most likely an xdist worker - we don't want these do do anything
        return
    pkg = [i for i in working_set if i.project_name == 'pkglib'][0]
    print "Building pkglib bdist_egg for tests"
    with chdir(pkg.location):
        subprocess.Popen([sys.executable, 'setup.py', 'bdist_egg']).communicate()
