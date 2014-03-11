# -*- coding: utf-8 -*-
"""
A top level helper so setup.py commands can be run on a number of
Python packages in a repository in the correct order.

Any failure in a sub-command will cause the loop to stop, unless it was a
test command in which case it will continue through all the packages, unless
the '-x' option was there in which case it will stop as normal.


If you have interdependent packages you need to setup in an environment, a
trick to sidestep the setup ordering problem is to run the following in order::

    python setup.py develop --no-deps
    python setup.py develop
"""
import sys
import subprocess

from pkglib.config import parse
from pkglib_util import cmdline


def setup():
    """ Mirror pkglib's setup() method for each sub-package in this repository.
    """
    top_level_parser = parse.get_pkg_cfg_parser()
    cfg = parse.parse_section(top_level_parser, 'multipkg', ['pkg_dirs'])
    rc = [0]
    for dirname in cfg['pkg_dirs']:
        with cmdline.chdir(dirname):
            # Update sub-package setup.cfg with top-level version if it's specified
            if 'version' in cfg:
                sub_parser = parse.get_pkg_cfg_parser()
                sub_cfg = parse.parse_pkg_metadata(sub_parser)
                if sub_cfg['version'] != cfg['version']:
                    print ("Updating setup.cfg version for {0}: {1} -> {2}"
                           .format(dirname, sub_cfg['version'], cfg['version']))
                    sub_parser.set('metadata', 'version', cfg['version'])
                    with open('setup.cfg', 'w') as sub_cfg_file:
                        sub_parser.write(sub_cfg_file)

            cmd = [sys.executable, "setup.py"] + sys.argv[1:]
            print ("In directory {0}: Running '{1}'"
                   .format(dirname, ' '.join(cmd)))
            try:
                cmdline.run(cmd, capture_stdout=False, bufsize=0)
            except subprocess.CalledProcessError as e:
                # Here we exit straight away, unless this was a run as
                # 'python setup.py test'. Reason for this is that we want to
                # run all the packages' tests through and gather the results.
                # Exception: using the -x/--exitfirst option.
                # For any other setup.py command, a failure here is likely
                # some sort of build or config issue and it's best not to
                # plow on.
                print "Command failed with exit code {0}".format(e.returncode)
                if 'test' in cmd and not '-x' in ' '.join(cmd)  \
                                 and not '--exitfirst' in ' '.join(cmd):
                    rc[0] = e.returncode
                else:
                    sys.exit(e.returncode)
    sys.exit(rc[0])
