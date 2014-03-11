#!/bin/env python
"""usage: %s [options] package [dest_dir]

Checkout a package from svn and set it up for develop in the currently
activated virtualenv. Can also recursively do the same for dependencies.

"""
import sys
import os
from optparse import OptionParser
from subprocess import CalledProcessError
from distutils import log

from pkglib import CONFIG
from pkglib.pypi import PyPi
from pkglib.errors import UserError
from pkglib.manage import checkout_pkg, setup_pkg, get_inhouse_dependencies
from pkglib.config import org

INSPECTED_PACKAGES = []


def get_options():
    """Get command-line options."""
    docstring = sys.modules[__name__].__doc__ % sys.argv[0]
    usage, _, description = docstring.split("\n", 2)

    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Verbose output")
    parser.add_option("-p", "--prefer-final",
                      action="store_true", dest="prefer_final", default=False,
                      help="When setting up the downloaded package, will install"
                      " non-dev versions of dependencies if available")
    parser.add_option("-P", "--pypi",
                      dest="pypi", default=CONFIG.pypi_url,
                      help="Override PyPi URI")
    parser.add_option("-d", "--deps",
                      action="store_true", dest="deps", default=False,
                      help="Will checkout and setup dependencies as well")
    parser.add_option("-r", "--recursive",
                      action="store_true", dest="recursive", default=False,
                      help="Will recursively follow the dependency chain. "
                      "This implies --deps has been set.")
    parser.add_option("-b", "--branch", dest="branch", default="trunk",
                      help="Branch to check out. Default is trunk")

    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("must supply a package name")
    if len(args) == 1:
        dir_name = normalize_dir(args[0])
        if os.path.isdir(dir_name):
            options.package = None
            options.dest_dir = dir_name
        else:
            options.package = args[0]
            options.dest_dir = os.path.abspath(args[0])
    if len(args) == 2:
        options.package = args[0]
        options.dest_dir = normalize_dir(args[1])
    if len(args) > 2:
        parser.error("unexpected token %s" % args[1])
    if options.recursive:
        options.deps = True
    return options


def process_pkg(pypi, pkg, dest_dir, options, recurse, indent=0):
    """ Checks out and sets up a package by name.
    """
    global INSPECTED_PACKAGES
    INSPECTED_PACKAGES.append(pkg)
    indent_txt = ' ' * indent
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
        checkout_pkg(dest_dir, pypi, pkg, options, options.branch, indent_txt)
        if recurse:
            # Do our children too
            for dep in get_inhouse_dependencies(pkg, indent_txt):
                log.info("%s Descending to dependency: %s" % (indent_txt, dep))
                dest_dir = os.path.join(os.path.dirname(dest_dir), dep)
                process_pkg(pypi, dep, dest_dir, options, options.recursive,
                            indent + 4)
    setup_pkg(sys.exec_prefix, dest_dir, options, indent_txt)


def normalize_dir(dir_name):
    for fn in (os.path.expanduser, os.path.expandvars, os.path.abspath):
        dir_name = fn(dir_name)
    return dir_name


def main():
    """Main method of pycheckout"""
    # TODO: allow cmdline override of org config?
    org.setup_global_org_config()
    options = get_options()

    try:
        pypi = PyPi(options.pypi)
        process_pkg(pypi, options.package, options.dest_dir, options,
                    options.deps)
        log.info("Done!")

    except (CalledProcessError, UserError), e:
        log.fatal(e)
        sys.exit(15)

if __name__ == "__main__":
    main()
