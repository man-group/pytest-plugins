#!/bin/env python
import sys
import warnings
import functools
import argparse
import termcolor
import os.path

from ConfigParser import ConfigParser
from pkglib import platypus
from pkglib import manage, CONFIG, config, errors

from pkglib.platypus import PlatError


def cprint(*args, **kwargs):
    kwargs = dict(kwargs)
    kwargs.setdefault("file", sys.stdout)
    termcolor.cprint(*args, **kwargs)


def statusmsg(msg, **kwargs):
    print msg


errormsg = functools.partial(cprint, color="red", file=sys.stderr)
warnmsg = functools.partial(cprint, color="yellow", file=sys.stdout)


def main(argv=sys.argv[1:]):
    """Script entry point.
    """
    # TODO: allow cmdline override of org config 
    config.setup_org_config()
    virtualenv_dir = sys.exec_prefix

    commands = {
        "use": use_command,
        "up": up_command,
        "develop": develop_command,
        "undevelop": undevelop_command,
        "info": info_command,
        "list": list_command,
        "versions": versions_command,
        "components": components_command,
    }

    try:
        ns = parse_options(argv)
    except errors.UserError, e:
        terminate(str(e))

    command = commands[ns.command]
    try:
        plat = platypus.Platypus(virtualenv_dir, quiet=ns.quiet, debug=ns.debug)
        command(plat, ns)
    except Exception as e:
        if plat.captured_out:
            errormsg("Sub-command output:")
            print plat.captured_out
        terminate(str(e))


def parse_options(argv):
    if not CONFIG.platform_packages:
        raise errors.UserError("No platform packages defined, please set [pkglib]:platform_packages "
                               "in your organisation config.")

    if not CONFIG.default_platform_package:
        raise errors.UserError("No default platform packages defined, please set "
                               "[pkglib]:default_platform_package in your organisation config.")

    description = ("Manages the installation of platform packages and their "
                   "components")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="hide process output")

    parser.add_argument("-d", "--debug", action="store_true",
                        help="will run subprocesses in verbose mode")

    subparsers = parser.add_subparsers(dest="command")

    parser_use = subparsers.add_parser(
        "use",
        help="Makes a deployed platform package available in the currently "
             "active virtualenv",
    )
    parser_use.add_argument(
        "package",
        nargs="?",
        default=CONFIG.default_platform_package,
        help="Name of the platform package",
    )
    parser_use.add_argument(
        "version",
        nargs="?",
        help="Version in the format rel-<number> for deployed packages or "
             "dev for the latest development snapshot",
    )

    parser_up = subparsers.add_parser(
        "up",
        help="Updates all dev packages that are installed in the current "
             "virtualenv",
    )
    # Hidden option to update only current packages to the latest release.
    parser_up.add_argument(
        "--current-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    parser_develop = subparsers.add_parser(
        "develop",
        help="Makes the source of a package available in the current "
             "virtualenv.",
    )

    parser_develop.add_argument(
        "package",
        nargs="?",
        help="Name of the package.",
    )

    parser_develop.add_argument(
        "location",
        nargs="?",
        help="Location where the source is checked out.",
    )

    parser_undevelop = subparsers.add_parser(
        "undevelop",
        help="Disables the source of a package from the current virtualenv."
    )
    parser_undevelop.add_argument(
        "package",
        nargs='+',
        help="name of the package."
    )

    parser_info = subparsers.add_parser(
        "info",
        help="Shows details of the platform packages that are "
             "active in the current virtualenv.",
    )

    parser_list = subparsers.add_parser(
        "list",
        help="Shows the available platform packages.",
    )

    parser_versions = subparsers.add_parser(
        "versions",
        help="Shows the versions of a platform package.",
    )

    parser_versions.add_argument(
        "package",
        help="Shows the names of the platform package.",
    )

    parser_components = subparsers.add_parser(
        "components",
        help="Shows the packages that are components of a platform package.",
    )

    parser_components.add_argument(
        "package",
        help="Shows the components of an installed platform package.",
    )

    with warnings.catch_warnings(DeprecationWarning):
        ns = parser.parse_args(argv)
    return ns


def use_command(plat, ns):
    def is_version(s):
        return s.startswith("rel-") or s == "dev"

    # Cater for the case there only the version has been specified.
    if not ns.version and is_version(ns.package):
        ns.version = ns.package
        ns.package = CONFIG.default_platform_package

    platform_packages = set(plat.get_platform_packages())
    if ns.package not in platform_packages:
        raise PlatError("package %s is not a platform package" % ns.package)

    if not ns.version:
        ns.version = "rel-current"

    version = ns.version
    if version.startswith("rel-"):
        version = version[4:]

    msg = "Using package %s, version %s." % (ns.package, ns.version)
    if ns.version == "dev":
        msg += " This might take some time."
    statusmsg(msg)
    plat.use(ns.package, version)


def up_command(plat, ns):
    installed = plat.get_installed_packages()
    current = plat.get_current_packages()
    platforms = plat.get_platform_packages()

    def is_needed(pkg, current_only):
        if pkg not in platforms:
            return False
        if pkg not in current:
            return False
        info = installed.get(pkg)
        if not info:
            return False
        if current_only:
            return not info.isdev
        return True

    if hasattr(ns, "package"):
        packages = [ns.package] if is_needed(ns.package, ns.current_only) else []
    else:
        packages = [pkg for pkg in platforms
                    if is_needed(pkg, ns.current_only)]

    for pkg in packages:
        statusmsg("Updating package %s. This might take some time." % pkg)
        plat.update(pkg)


def develop_command(plat, ns):
    """FIXME: Refactor in smaller functions to make this digestable.
    """
    if not any((ns.package, ns.location)):
        errormsg("At least one package or location must be specified.")
        sys.exit(2)

    # Only one argument was provided.  ns.package could hold a package name
    # or a path to an existing source check-out.
    if not ns.location:
        ns.location = os.path.abspath(ns.package)
        # If the directory does not exist ns.package must be meant to
        # specify a package name.  Use the non-existing directory as the
        # default where the package is checked out.
        # If the directory exists also use it as ns.location.  Set ns.package
        # from the name as per setup.cfg that should live in the directory.
        setup_fname = os.path.join(ns.location, "setup.cfg")
        if os.path.isfile(setup_fname):
            cfg = ConfigParser()
            cfg.read(setup_fname)
            try:
                ns.package = cfg.get("metadata", "name")
            except:
                pass
    else:
        # Make sure we use a fully qualified path
        ns.location = os.path.abspath(ns.location)
    if not ns.package:
        errormsg("Unable to determine package name from %s" % ns.location)

    # Check if the package is already checked-out.
    pkg_info = plat.get_installed_version(ns.package)
    if pkg_info and pkg_info.isdevsrc and pkg_info.source != ns.location:
        warnmsg("Package %s is also checked out at %s" % (ns.package,
                pkg_info.source))
        if not prompt("Continue?"):
            terminate(rc=0)

    # Verify that the package is a platform package or a component of a
    # platform package.
    platforms = plat.get_platform_packages()
    platform_pkg = ns.package if ns.package in platforms else None
    if not platform_pkg:
        for pkg in platforms:
            try:
                deps = plat.get_package_dependencies(pkg)
                if ns.package in deps:
                    platform_pkg = pkg
                    break
            except ValueError:
                pass
    if not platform_pkg:
        raise PlatError("Package %s is neither a platform package nor a "
                        "component of a platform package" % ns.package)

    # If the package is a component of a platform package then verify that
    # the platform package version is at "dev"
    if platform_pkg != ns.package:
        plat_info = plat.get_installed_version(platform_pkg)
        if plat_info and not plat_info.isdev:
            warnmsg("Package %s is a component of platform package %s which "
                    "is not a dev version." % (ns.package,
                    platform_pkg))
            if not prompt("Use dev version of %s?" % platform_pkg):
                terminate(rc=0)
            use_opts = argparse.Namespace(package=platform_pkg, version="dev",
                                          quiet=ns.quiet, debug=ns.debug)
            use_command(plat, use_opts)
        else:
            up_opts = argparse.Namespace(package=platform_pkg,
                                         current_only=False, quiet=ns.quiet,
                                         debug=ns.debug)
            up_command(plat, up_opts)

    # Check the platform or component package out
    statusmsg("Develop package %s at %s" % (ns.package, ns.location))
    plat.develop(ns.package, ns.location)


def undevelop_command(plat, ns):
    platforms = set([])
    for package in ns.package:
        info = plat.get_installed_version(package)
        if not info:
            raise PlatError("package %s is not installed" % package)
        if not info.isdevsrc:
            raise PlatError("package %s is not a source installation" % package)

        platforms.union(plat.get_owning_platforms(package))
        statusmsg("Undevelop package %s at %s" % (package, info.source))
        plat.undevelop(package)

    # We just moved to the most recent development version of the component
    # that got undeveloped.  We need to update all components in the platforms
    # that this component is a member of to make sure all components are
    # in sync with each other.
    for platform in platforms:
        up_opts = argparse.Namespace(package=platform, current_only=False,
                                     quiet=ns.quiet, debug=ns.debug)
        up_command(plat, up_opts)


def info_command(plat, ns):
    info, source_checkouts = plat.get_packages_information()
    for pkg, pkg_info in info:
        statusmsg(": ".join((pkg, pkg_info["version"])))
        #dependencies = pkg_info.get("dependencies")
        #if dependencies:
    if source_checkouts:
        statusmsg("Other source checkouts:")
        for dep in source_checkouts:
            statusmsg("    %s: %s" % (dep.name, dep.version))


def list_command(plat, ns):
    platforms = plat.get_platform_packages()
    for pkg in platforms:
        version = plat.get_current_version(pkg)
        meta = plat.get_package_metadata(pkg, version)
        statusmsg("%s: %s" % (pkg, meta.get("summary", "")))


def versions_command(plat, ns):
    platforms = plat.get_platform_packages()
    if ns.package not in platforms:
        raise PlatError("Package %s is not a platform package" % ns.package)

    pkg_info = plat.get_installed_version(ns.package)
    if not pkg_info:
        version = plat.get_current_version(ns.package)
    else:
        version = pkg_info.version

    meta = plat.get_package_metadata(ns.package, version)
    platform = "%s: %s" % (ns.package, meta.get("summary", ""))
    statusmsg(platform)

    versions = plat.get_available_versions(ns.package)
    for version in versions:
        statusmsg("    " + version)


def components_command(plat, ns):
    platforms = plat.get_platform_packages()
    if ns.package not in platforms:
        raise PlatError("Package %s is not a platform package" % ns.package)

    pkg_info = plat.get_installed_version(ns.package)
    if not pkg_info:
        raise PlatError("Package %s is not installed" % ns.package)

    meta = plat.get_package_metadata(ns.package, pkg_info.version)
    platform = "%s (%s): %s" % (ns.package, pkg_info.version,
               meta.get("summary", ""))
    statusmsg(platform)

    components = plat.get_package_dependencies(ns.package).itervalues()
    components = ["%s (%s)" % (pkg.name, pkg.version) for pkg in components
                               if pkg and manage.is_inhouse_package(pkg.name)]
    components.sort()
    for component in components:
        statusmsg("    " + component)


def terminate(text="", rc=2):
    if text:
        errormsg(text)
    sys.exit(rc)


def prompt(text):
    answer = raw_input(termcolor.colored(text + " [Y/n]: ", "yellow")).upper()
    return answer != "N"
