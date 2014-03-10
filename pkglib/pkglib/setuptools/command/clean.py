import glob
import os.path
import re
import shutil
import sys

from distutils import log
from distutils.command.clean import clean as _clean

from pkg_resources import working_set

from pkglib.cmdline import chdir

from .base import CommandMixin, fetch_build_eggs

IGNORE_DIRECTORIES = ['.svn', r'[A-Za-z0-9_-]+.egg']


class clean(_clean, CommandMixin):
    """Clean up temporary files, build dirs and the package environment"""
    description = __doc__

    user_options = _clean.user_options + [
        ('tidy', None, "clean up the package environment in addition to build dirs"),
        ('packages', None, "clean up unused packages in site-packages"),
    ]
    boolean_options = _clean.boolean_options + ['tidy', 'packages']

    victim_whitelist = [
         'pip',
         'distribute',
         'setuptools',
    ]

    open_files = []

    def initialize_options(self):
        _clean.initialize_options(self)
        self.tidy = False
        self.packages = False
        self._ignore_directories_patt = [re.compile(d) for d in IGNORE_DIRECTORIES]

    def finalize_options(self):
        _clean.finalize_options(self)
        self.all = self.all or self.tidy

    def filter_victim(self, victim):
        basename = os.path.basename(victim)
        for i in self.victim_whitelist:
            if basename.startswith(i):
                return False
        if not victim.endswith('.egg'):
            return False
        return True

    def filter_open_files(self, victim):
        # Check for file locks
        for pid, filename in self.open_files:
            if victim in filename:
                log.warn("Can't delete %s, locked by pid : %s" % (victim, pid))
                return False
        return True

    def find_victims(self):
        active_things = set([i.location for i in working_set if
                            i.location.startswith(sys.exec_prefix)])
        installed_things = set([i for i in os.listdir(self.get_site_packages())
                                if self.filter_victim(i)])
        victims = installed_things.difference(active_things)
        victims = filter(self.filter_open_files, victims)
        return sorted(victims)

    def clean_site_packages(self):
        for victim in self.find_victims():
            if os.path.isdir(victim):
                self.execute(shutil.rmtree, (victim,),
                             'Deleting directory {}'.format(victim))
            else:
                self.execute(os.unlink, (victim,),
                             'Deleting {}'.format(victim))

    def run(self):
        if self.packages:
            self.clean_site_packages()
        _clean.run(self)
        if self.tidy:
            self.remove_objects(['build', 'dist', 'htmlcov'])
            self.remove_objects([self.get_finalized_command('egg_info').egg_info])
            self.remove_objects(self._build_ext_outputs())
            self.remove_from_dir('.', ['*.pyc', '*.pyo', '__pycache__'])
            self.remove_from_dir('.', ['.coverage.*'])

    def _is_ignored_directory(self, name):
        return any(patt.match(name) for patt in self._ignore_directories_patt)

    def _build_ext_outputs(self):
        """list any built artifacts that may pollute the source directory."""
        build_ext = self.get_finalized_command('build_ext')
        if build_ext.uses_cython():
            fetch_build_eggs(['Cython'], dist=self.distribution)
            from Cython.Distutils import build_ext as cython_build_ext  # @UnresolvedImport
            self.distribution.cmdclass['cython_build_ext'] = cython_build_ext
            self.distribution.command_obj['cython_build_ext'] = cython_build_ext(self.distribution)
            self.distribution.command_obj['cython_build_ext'].inplace = build_ext.inplace
            build_ext = self.get_finalized_command('cython_build_ext')
            for ext in build_ext.extensions:
                for name in self._cython_new_sources(build_ext, ext.sources, ext):
                    yield name

        for name in build_ext.get_outputs():
            yield name

        # cf. distribute setuptools.command.build_ext.build_ext.copy_extensions_to_source
        build_py = self.get_finalized_command('build_py')
        for ext in build_ext.extensions:
            fullname = build_ext.get_ext_fullname(ext.name)
            filename = build_ext.get_ext_filename(fullname)
            modpath = fullname.split('.')
            package = '.'.join(modpath[:-1])
            package_dir = build_py.get_package_dir(package)
            yield os.path.join(package_dir, os.path.basename(filename))
            # stub is already included in get_outputs()

    def _cython_new_sources(self, cmd, sources, extension):
        """list the generated sources that Cython would generate for an extension."""
        # cf. Cython.Distutils.build_ext.build_ext.cython_sources
        target_ext = '.cpp' if (cmd.cython_cplus or getattr(extension, 'cython_cplus', 0) or
                                (extension.language and extension.language.lower() == 'c++')) else '.c'
        target_dir = (os.path.join(cmd.build_temp, "pyrex", *extension.name.split('.')[:-1]) if
                      not cmd.inplace and (cmd.cython_c_in_temp or getattr(extension, 'cython_c_in_temp', 0)) else
                      None)

        for source in sources:
            (base, ext) = os.path.splitext(os.path.basename(source))
            if ext in ('.py', '.pyx'):              # Cython source file
                output_dir = os.path.dirname(source) if target_dir is None else target_dir
                yield os.path.join(output_dir, base + target_ext)

    def remove_objects(self, names):
        """deletes any instances of the named directories/files, relative to this directory"""
        for name in names:
            self.remove_object(os.getcwd(), name)

    def remove_object(self, dirname, name):
        if os.path.isdir(name) and not self._is_ignored_directory(name):
            self.execute(shutil.rmtree, (name,), 'Deleting directory %s/%s' % (dirname, name))
        elif os.path.isfile(name):
            self.execute(os.remove, (name,), 'Deleting file %s/%s' % (dirname, name))

    def remove_from_dir(self, topdir, names):
        """recursively deletes any instances of names (glob matching)
        which exist in top-level directory dirpath
        """
        def check_and_remove(adir):
            with chdir(adir):
                for name in names:
                    for item in glob.iglob(name):
                        self.remove_object(adir, item)

        top = os.path.abspath(topdir)
        check_and_remove(top)
        if os.path.isdir(top):
            for dirpath, dirnames, _ in os.walk(top):
                for obj in dirnames:
                    # see if there are any matches in this directory
                    check_and_remove(os.path.join(os.path.join(dirpath, obj)))
