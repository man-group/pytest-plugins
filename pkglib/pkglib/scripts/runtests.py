"""
Run a test-package's tests. This exactly mimics the behavior of running 'python setup.py test'
in the original package, even down to the point of picking up any py.test / setup.cfg
configuration from the original source package.
"""
import sys
from os.path import join, isfile

from pkg_resources import working_set
from setuptools import Distribution

from pkglib import CONFIG
from pkglib.config import org
from pkglib.setuptools.command.test import test


def main(argv=None, **kw):
    """ Run a test package's tests.
    """
    org.setup_global_org_config()

    USAGE = """\
usage: %(script)s <package name> [test options]
   or: %(script)s --help
""" % {'script': sys.argv[0] or 'runtests'}

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print "Please specify a package name."
        print USAGE
        sys.exit(1)

    pkg_name, argv = argv[0], argv[1:]
    test_pkg_name = 'test.%s' % pkg_name

    # Find our
    real_dist = [i for i in working_set if i.project_name == pkg_name]
    if not real_dist:
        print "Package %s is not installed" % pkg_name
        sys.exit(1)
    real_dist = real_dist[0]

    test_dist = [i for i in working_set if i.project_name == test_pkg_name]
    if not test_dist:
        print "Test package %s is not installed" % test_pkg_name
        sys.exit(1)
    test_dist = test_dist[0]

    # Construct a distutils.Distribtion class from the pkg_resources.Distribution
    # of the real package so we can pass it into the test command class.
    # We have checked that the packages are already installed so we set the install
    # requirements to blank.

    args = {'name': real_dist.project_name,
            'install_requires': [],
            'tests_require': [],
            'namespace_packages': list(real_dist._get_metadata('namespace_packages')),
            'packages': [real_dist.project_name],
            }
    real_cmd_dist = Distribution(args)
    cmd = test(real_cmd_dist)
    cmd.args = argv

    # Read in the test options saved away during egg_info and set the command defaults,
    # this would normally be done by the setup() method via the Distribution class
    test_options = join(test_dist.location, 'EGG-INFO', 'test_options.txt')
    if isfile(test_options):
        real_cmd_dist.parse_config_files([test_options])
    for k, v in real_cmd_dist.get_option_dict('test').items():
        print "Found test option in %s: %s = %s" % (v[0], k, v[1])
        setattr(cmd, k, v[1])

    # Finalize and run the command, overriding the test root to be inside the test egg
    cmd.finalize_options()
    cmd.test_root = join(test_dist.location, CONFIG.test_egg_namespace ,
                         real_dist.project_name.replace('.', '/'))
    # Pylint is only for regular Jenkins jobs, this in itself should not trigger even if
    # running under Jenkins
    cmd.no_pylint = True
    cmd.run()
