from __future__ import absolute_import

import sys
import os.path
import re

from distutils import log
import pkg_resources
from setuptools.command.easy_install import (easy_install as _easy_install,
                                             get_script_header, sys_executable,
                                             is_64bit, resource_string)

from pkglib import egg_cache
from .base import CommandMixin


# from: setuptools.command.easy_install.get_script_args
# from: zc.buildout.easy_install._generate_scripts
def get_script_args(dist, executable=sys_executable, wininst=False):
    """Yield write_script() argument tuples for a distribution's entrypoints"""
    header = get_script_header("", executable, wininst)
    for group in 'console_scripts', 'gui_scripts':
        for name, ep in dist.get_entry_map(group).items():
            script_text = """import sys
if __name__ == '__main__':
    import {module_name}
    sys.exit({module_name}.{attrs}())
""".format(module_name=ep.module_name, attrs='.'.join(ep.attrs),
           )
            if sys.platform == 'win32' or wininst:
                # On Windows/wininst, add a .py extension and an .exe launcher
                if group == 'gui_scripts':
                    ext, launcher = '-script.pyw', 'gui.exe'
                    old = ['.pyw']
                    new_header = re.sub('(?i)python.exe', 'pythonw.exe', header)
                else:
                    ext, launcher = '-script.py', 'cli.exe'
                    old = ['.py', '.pyc', '.pyo']
                    new_header = re.sub('(?i)pythonw.exe', 'python.exe', header)
                if is_64bit():
                    launcher = launcher.replace(".", "-64.")
                else:
                    launcher = launcher.replace(".", "-32.")
                if os.path.exists(new_header[2:-1]) or sys.platform != 'win32':
                    hdr = new_header
                else:
                    hdr = header
                yield (name+ext, hdr+script_text, 't', [name+x for x in old])
                yield (
                    name+'.exe', resource_string('setuptools', launcher),
                    'b'  # write in binary mode
                )
            else:
                # On other platforms, we assume the right thing to do is to
                # just write the stub with no extension.
                yield (name, header+script_text)


def monkeypatch(module, attr):
    def inner(replacement):
        setattr(sys.modules[module], attr, replacement)
        return replacement
    return inner


@monkeypatch('setuptools.command.easy_install', 'easy_install')
@monkeypatch('setuptools.command.develop', 'easy_install')
class easy_install(_easy_install, CommandMixin):
    pkglib_bootstrap = False

    create_index = egg_cache.EggCacheAwarePackageIndex

    def __init__(self, dist, **kw):
        # This is what stops things being installed in the local directory,
        # and instead _always_ dropped into site-packages.
        # Vanilla easy_install takes offence to this with a sandbox violation,
        # so we need to detect when we're being setup by easy_install and not do this.
        if type(self).pkglib_bootstrap and 'easy_install' not in sys.argv[0]:
            kw.pop('install_dir', None)
        _easy_install.__init__(self, dist, **kw)

    def initialize_options(self):
        _easy_install.initialize_options(self)

    def finalize_options(self):
        _easy_install.finalize_options(self)
        self.set_undefined_options('install',
                                   ('install_data', 'install_data'),
                                   )

    def process_distribution(self, requirement, dist, deps=True, *info):
        if dist in self.local_index[dist.key]:
            self.local_index.remove(dist)
        return _easy_install.process_distribution(self, requirement, dist, deps,
                                                  *info)

    def install_wrapper_scripts(self, dist):
        if not self.exclude_scripts:
            for args in get_script_args(dist):
                self.write_script(*args)

    def install_item(self, spec, download, tmpdir, deps, install_needed=False):
        """ The only difference between this and the standard implementation is that it doesn't copy
            eggs from the egg cache but links to them in place.
        """
        # Installation is also needed if file in tmpdir or is not an egg
        install_needed = install_needed or self.always_copy
        install_needed = install_needed or os.path.dirname(download) == tmpdir
        install_needed = install_needed or not download.endswith('.egg')
        install_needed = install_needed or (
            self.always_copy_from is not None and
            os.path.dirname(pkg_resources.normalize_path(download)) ==
            pkg_resources.normalize_path(self.always_copy_from)
        )

        # This is the only bit that is different:
        #  <---------- here ----------------->
        if not egg_cache.is_from_egg_cache(download) and spec and not install_needed:
            # at this point, we know it's a local .egg, we just don't know if
            # it's already installed.
            for dist in self.local_index[spec.project_name]:
                if dist.location == download:
                    break
            else:
                install_needed = True  # it's not in the local index

        log.info("Processing %s", os.path.basename(download))

        if install_needed:
            dists = self.install_eggs(spec, download, tmpdir)
            for dist in dists:
                self.process_distribution(spec, dist, deps)
        else:
            dists = [self.egg_distribution(download)]
            self.process_distribution(spec, dists[0], deps, "Using")

        if spec is not None:
            for dist in dists:
                if dist in spec:
                    return dist
