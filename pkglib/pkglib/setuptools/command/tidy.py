import os.path
import shutil
import glob
import re

from setuptools import Command

from pkglib.manage import chdir

from base import CommandMixin

IGNORE_DIRECTORIES = ['.svn', r'[A-Za-z0-9_-]+.egg']

class tidy(Command, CommandMixin):
    """ Tidy the package environment """
    description = "Tidy up the desktop environment"

    user_options = [
                   ]
    boolean_options = [
                      ]


    def initialize_options(self):
        self._ignore_directories_patt = []
        for d in IGNORE_DIRECTORIES:
            self._ignore_directories_patt.append(re.compile(d))

    def finalize_options(self):
        pass

    def run(self):
        self.remove_objects(['build', 'dist', 'htmlcov'])
        self.remove_from_dir('.', ['*.pyc', '*.pyo', '__pycache__'])

    def _is_ignored_directory(self, name):
        for patt in self._ignore_directories_patt:
            if patt.match(name):
                return True
        return False

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
            for dirpath, dirnames, filenames in os.walk(top):
                for obj in dirnames:
                    # see if there are any matches in this directory
                    check_and_remove(os.path.join(os.path.join(dirpath, obj)))
