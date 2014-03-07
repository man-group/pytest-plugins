import os
import distutils

from setuptools import Command
from pkg_resources import normalize_path
from contextlib import contextmanager

from .base import CommandMixin, get_easy_install_cmd
from pkglib.egg_cache import get_egg_cache_paths


@contextmanager
def pip_logging_to_distutils_log():
    # Pip has some non-standard log levels, we'll wire them back into
    # regular logging or they get hidden from the user
    from pip.log import logger
    levels = {
        'notify': 'info',
        'debug': 'debug',
        'info': 'info',
        'error': 'error',
        'fatal': 'fatal',
        'warn': 'warn',
    }
    old_levels = dict((k, getattr(logger, k)) for k in levels.keys())
    for k, v in levels.items():
        setattr(logger, k, getattr(distutils.log, v))
    try:
        yield None
    finally:
        for k, v in old_levels.items():
            setattr(logger, k, v)


@contextmanager
def patch_UninstallPathSet(egg_caches, install_dir):
    # pip uninstall doesn't realise that you can remove an entry from the virtualenv
    # easy-install.pth file even if the egg itself is outside the virtualenv i.e. in
    # the egg cache.  Fix it by adjusting the pth file and entry.
    from pip import req
    ei_pth_file = os.path.join(normalize_path(install_dir), 'easy-install.pth')

    class UninstallPathSet(req.UninstallPathSet):
        def _can_uninstall(self):
            return True

        def add_pth(self, pth_file, entry):
            if any(pth_file.startswith(egg_cache) for egg_cache in egg_caches):
                pth_file, entry = ei_pth_file, self.dist.location
            super(UninstallPathSet, self).add_pth(pth_file, entry)
    req.UninstallPathSet, old_UninstallPathSet = UninstallPathSet, req.UninstallPathSet
    try:
        yield None
    finally:
        req.UninstallPathSet = old_UninstallPathSet


class pyuninstall(Command, CommandMixin):
    """ Remove a package. Calls pip.uninstall """
    description = "Remove a package. Uses pip.uninstall"
    command_consumes_arguments = True

    user_options = [
        ('yes', 'y', "Don't ask for confirmation of uninstall deletions."),
    ]
    boolean_options = [
        'yes',
    ]

    def initialize_options(self):
        self.yes = False
        self.args = []

    def finalize_options(self):
        pass

    def run(self):
        """ Wire in the pip uninstall command
        """
        with pip_logging_to_distutils_log():
            # Lazy imports here to allow pkglib to bootstrap itself.
            from pip import req, exceptions

            rs = req.RequirementSet(build_dir=None, src_dir=None, download_dir=None)
            for name in self.args:
                rs.add_requirement(req.InstallRequirement.from_line(name))

            install_dir = get_easy_install_cmd(self.distribution).install_dir
            with patch_UninstallPathSet(get_egg_cache_paths(), install_dir):
                try:
                    rs.uninstall(auto_confirm=self.yes)
                except exceptions.UninstallationError as e:
                    distutils.log.fatal(e)
