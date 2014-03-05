#!/bin/env python
import sys
import os
import subprocess
import itertools
import pkg_resources
from os import path

from pkglib import pypi, CONFIG, util
import errors


__all__ = ["Platypus", "PlatError"]


class PackageInfo(object):

    def __init__(self, name, version, source):
        self.name = name
        self.version = version
        self.source = source

    @property
    def isrelsrc(self):
        return self.isrel and self.issrc

    @property
    def isdevsrc(self):
        return (self.isdev and
                self.issrc and
                not self.source.startswith(sys.prefix))

    @property
    def issrc(self):
        return self.source and os.access(self.source, os.W_OK)

    @property
    def isdev(self):
        return util.is_dev_version(self.version)

    @property
    def isrel(self):
        return not self.isdev


class PlatError(Exception):
    pass


class Platypus(object):

    def __init__(self, virtualenv_dir, quiet=False, debug=False, platform_packages=None):
        """Constructor.
        """
        self.quiet = quiet
        self.debug = debug
        self.virtualenv_dir = virtualenv_dir
        self.pyuninstall = path.join(virtualenv_dir, "bin", "pyuninstall")
        self.pyinstall = path.join(virtualenv_dir, "bin", "pyinstall")
        self.pycheckout = path.join(virtualenv_dir, "bin", "pycheckout")
        self.platform_packages = (platform_packages or
                                  CONFIG.platform_packages)
        self.pypi = pypi.PyPi()
        self.captured_out = ""

    def run(self, cmd):
        stdout = None
        stderr = None
        if self.quiet:
            stdout = subprocess.PIPE
            stderr = subprocess.STDOUT
        if not self.quiet:
            print "Running sub-command: %r" % ' '.join(cmd)
        p = subprocess.Popen(cmd, cwd='/', stdout=stdout, stderr=stderr)
        self.captured_out = p.communicate()[0]
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, ' '.join(cmd))

    def update(self, package):
        """Updates a package to the latest available version.
        """
        # Nothing to update if the package isn't installed.
        pkg_info = self.get_installed_version(package)
        if not pkg_info:
            return

        # Don't update a package if it's not a development version or
        # the currently installed version is equal to the most recent (ie
        # "current") version
        if (not pkg_info.isdev and
            pkg_info.version == self.get_current_version(package)):
            return

        args = [self.pyinstall]
        if self.debug:
            args.append("-v")
        if pkg_info.isdev:
            args.append("--dev")
        args.append(package)

        self.run(args)

    def use(self, package, version):
        """Makes a platform package available from a virtualenv.

        Parameters
        ----------
        package : `str`
            Name of the platform package.
        version : `str`
            Version of the platform package.

        """
        is_current = (version == "current")
        if is_current:
            version = self.get_current_version(package)

        if version not in ("dev", "current"):
            available_versions = set(self.get_available_versions(package))
            if version not in available_versions:
                raise PlatError('%(pkg)s has no release version %(ver)s. Use '
                                '"plat versions %(pkg)s" to see the available '
                                'versions' % dict(pkg=package, ver=version))
        if self.get_installed_version(package) != version:
            argv = []
            if self.debug:
                argv.append("-v")
            if version == "dev":
                argv.extend(["--dev", package])
            else:
                argv.append("".join((package, "==", version)))

            argv = list(itertools.chain([self.pyinstall], argv))

            if "http_proxy" in os.environ:
                del os.environ["http_proxy"]
            self.run(argv)
        self.update_current_packages(package, is_current)

    def develop(self, package, location):
        args = [self.pycheckout]
        if self.debug:
            args.append("-v")
        args.extend([package, location])
        self.run(args)
        self.update_current_packages(package, False)

    def undevelop(self, package):
        # Uninstall the package or component
        args = [self.pyuninstall]
        if self.debug:
            args.append("-v")
        args.extend(["--yes", package])
        self.run(args)
        # Need to re-install the dev version of the package or component
        # to replace the source version.
        args = [self.pyinstall]
        if self.debug:
            args.append("-v")
        args.extend(["--dev", package])
        self.run(args)

    def get_owning_platforms(self, package):
        info, _ = self.get_packages_information()
        platforms = [pkg for pkg, pkg_info in info
                     if (package == pkg or
                         package in dict(pkg_info.get("dependencies", [])).keys())]
        return platforms

    def get_package_metadata(self, package, version):
        metadata = self.pypi.get_package_metadata(package, version)
        return metadata

    def get_packages_information(self):
        platform = self.get_platform_packages()
        current = set(self.get_current_packages())
        installed = self.get_installed_packages()

        def platform_version(pkg):
            if pkg not in installed:
                return "not installed"
            pkg_info = installed[pkg]
            version = pkg_info.version
            if pkg_info.isdevsrc:
                version = "source (%s: %s)" % (version, pkg_info.source)
            elif pkg_info.isdev:
                version = "dev (%s)" % version
            elif pkg in current:
                version = "rel-current (%s)" % version
            else:
                version = "rel-fixed (%s)" % version
            return version

        def platform_dependencies(pkg):
            if pkg not in platform or pkg not in installed:
                return []
            pkg_info = installed[pkg]
            if pkg_info.isrel:
                return []
            dependencies = self.get_package_dependencies(pkg)
            dependencies = [(dep_info.name, {"version": platform_version(dep_info.name)})
                            for dep_info in dependencies.itervalues()
                            if dep_info.isdevsrc]
            return dependencies

        info = [(pkg, {"version": platform_version(pkg)}) for pkg in platform]
        for pkg, pkg_info in info:
            dependencies = platform_dependencies(pkg)
            if dependencies:
                pkg_info["dependencies"] = dependencies

        source_checkouts = [i for i in installed.values()
                            if i.isdevsrc
                            and not i.name in platform]
        return info, source_checkouts

    def get_package_dependencies(self, package):
        seen = set()
        todo = set([package])
        all_deps = {}

        def check_dependencies(package):
            deps = get_package_dependencies(package)
            seen.add(package)
            all_deps.update(deps)
            todo.update(deps.iterkeys())
            todo.difference_update(seen)

        while todo:
            pkg = todo.pop()
            check_dependencies(pkg)
        return all_deps

    def get_current_version(self, package, python_version="py2.6"):
        """Returns the most recent package version that's available.
        """
        versions = self.get_available_versions(package)
        return versions[0] if versions else ""

    def get_available_versions(self, package):
        versions = self.pypi.get_available_versions(package)
        return versions

    def get_installed_packages(self):
        all_pkgs = ((pkg.key, PackageInfo(pkg.key, pkg.version, pkg.location))
                    for pkg in pkg_resources.working_set if pkg)
        all_pkgs = dict(all_pkgs)
        return all_pkgs

    def update_current_packages(self, package, is_current):
        """Updates the current_packages text file where we record which of the
        installed packages should automatically be upgraded with the most recent
        release.
        """
        fname = self.get_current_packages_file()
        current_packages = set()
        if path.exists(fname):
            with open(fname) as f:
                current_packages.update([line.strip() for line in f])

        if is_current:
            current_packages.add(package)
        else:
            current_packages.discard(package)
        with open(fname, "w") as f:
            for line in sorted(current_packages):
                f.writelines([line, "\n"])

    def get_installed_version(self, package):
        """Returns the package version that is currently installed or
        None if the package is not installed.
        """
        packages = self.get_installed_packages()
        return packages.get(package, None)

    def get_platform_packages(self):
        """Returns a list of all platform packages.
        """
        return self.platform_packages

    def get_current_packages(self):
        """Returns a list of all packages that should be kept current.
        """
        res = []
        all_packages = self.get_installed_packages()
        # We implicitly include dev platform packages here, regardless of how
        # they are setup in the config file
        for pkg in all_packages:
            if pkg in self.platform_packages \
               and all_packages[pkg].isdev  \
               and not all_packages[pkg].isdevsrc:
                res.append(pkg)

        fname = self.get_current_packages_file()
        if not path.exists(fname):
            return res

        packages = (line.strip().split("#")[0] for line in open(fname))
        packages = [pkg for pkg in packages if pkg]

        # We also need to strip out source packages here in case
        # they were setup for development outside plat
        packages = [pkg for pkg in packages if pkg in all_packages
                    and not all_packages[pkg].isdevsrc]

        return list(set(packages + res))

    def get_current_packages_file(self):
        """Returns the name of the file that is used to record the packages that
        should be kept current.
        """
        return path.join(self.virtualenv_dir, "current-packages.txt")


def get_package_dependencies(package_name):
    dist = pkg_resources.working_set.by_key.get(package_name)
    if not dist:
        raise errors.UserError("Package %s is not installed" % package_name)

    deps = (pkg_resources.working_set.by_key.get(req.key)
            for req in dist.requires())
    deps = ((dist.key, PackageInfo(dist.key, dist.version, dist.location))
             for dist in deps if dist)
    deps = dict(deps)
    return deps


def sort_versions(versions):
    def normalize(a, b):
        try:
            ai = int(a)
            bi = int(b)
            return ai, bi
        except ValueError:
            return a, b

    def version_cmp(al, bl):
        al = al.split(".")
        bl = bl.split(".")

        for a, b in itertools.izip(al, bl):
            a, b = normalize(a, b)
            rc = cmp(a, b)
            if rc:
                return rc
        return len(al) - len(al)

    versions.sort(version_cmp, reverse=True)
