#! /bin/env python

import sys
import os.path
import subprocess

this_dir = os.path.dirname(__file__)


def main():
    top = os.getcwd()
    run(top)


def find_setup_py_dir(dirname):
    orig_dirname = dirname
    while dirname.count('/') > 2:
        if 'setup.py' in os.listdir(dirname):
            break
        dirname = os.path.dirname(dirname)
    else:
        raise RuntimeError('setup.py not found in %s or any parent' % orig_dirname)
    return dirname


def run(dirname=this_dir):
    # check that setup.py exists in this directory .. or any parent .
    dirname = find_setup_py_dir(dirname)
    setup_py = os.path.abspath(os.path.join(dirname, 'setup.py'))
    cmd = ['python', setup_py, 'tidy']
    print 'tidying "%s"' % dirname
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdoutdata, _ = p.communicate()
    sys.stdout.write(stdoutdata)


if __name__ == '__main__':
    main()
