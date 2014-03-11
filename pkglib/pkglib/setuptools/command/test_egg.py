import os
import shutil

from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
from setuptools import find_packages

from pkglib import CONFIG
from pkglib.config import parse


from .base import CommandMixin, write_text


NAMESPACE_PACKAGE_INIT = """
__import__('pkg_resources').declare_namespace(__name__)
"""


class test_egg(_bdist_egg, CommandMixin):
    """ Build an egg that just contains the test artifacts.
    """
    def finalize_options(self):

        # Where the tests are found
        dist = self.distribution
        self.test_dir = os.path.join(os.getcwd(), 'tests')

        # Where in the build tree they're going
        build_py = self.get_finalized_command('build_py')
        self.build_lib = build_py.build_lib
        self.dest_dir = os.path.join(self.build_lib, CONFIG.test_egg_namespace,
                                     dist.get_name().replace('.', os.path.sep))

        # This stops the regular bdist builder from triggering, allowing us to
        # craft our own package underneath the regular build tree
        self.skip_build = True

        # Adjust the package metadata to suit our test package
        self.old_name = dist.metadata.name
        dist.metadata.name = 'test.%s' % self.old_name
        dist.namespace_packages = ([CONFIG.test_egg_namespace] +
                                   ['%s.%s' % (CONFIG.test_egg_namespace, i)
                                    for i in dist.namespace_packages])
        dist.entry_points = {}

        # Set the install requirements to be the test requirements of the
        # original, plus a direct pin to the original version.
        self.old_version = self.get_finalized_command('egg_info').egg_version
        dist.install_requires = (dist.tests_require +
                                 ['%s==%s' % (self.old_name,
                                              self.old_version)])
        _bdist_egg.finalize_options(self)

    def get_file_dest(self, filename):
        return os.path.join(self.dest_dir,
                            (filename.split(self.test_dir + os.path.sep)[1]))

    def _copy_file(self, src, dest):
        test_dir = os.path.abspath(os.path.join(dest, os.pardir))
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        shutil.copyfile(src, dest)

    def create_init_files(self, top_dir):
        """
        Creates empty __init__.py files for all dirs under and including
        a given directory if they are missing.
        """
        if not os.path.isdir(top_dir):
            return

        for root, dirs, _ in os.walk(top_dir):
            if '.svn' in dirs:
                dirs.remove('.svn')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            pkg_init = os.path.join(root, '__init__.py')
            if not os.path.isfile(pkg_init):
                self.execute(write_text, (pkg_init, '',),
                             "creating missing package file at %s" % pkg_init)

    def create_ns_pkg_files(self, top_dir):
        """
        Creates ns package files where needed, eg in:
        build/lib/tests
        build/lib/tests/acme
        """
        if not os.path.isdir(top_dir):
            return

        for ns in self.distribution.namespace_packages:
            ns_dir = os.path.join(top_dir, ns.replace('.', os.path.sep))
            ns_init = os.path.join(ns_dir, '__init__.py')
            if not os.path.isfile(ns_init):
                self.execute(write_text, (ns_init, NAMESPACE_PACKAGE_INIT,),
                             "creating missing namespace package file at: %s"
                             % ns_init)

    def create_pytest_config(self, filename):
        """
        Extracts the pytest specific sections from setup.cfg and puts them
        into a separate config file in the build dir
        """
        parser = parse.get_pkg_cfg_parser()
        [parser.remove_section(s) for s in parser.sections() if s != 'pytest']
        if parser.has_section('pytest'):
            with open(filename, 'wt') as f:
                parser.write(f)

    def run(self):
        self.create_init_files(self.test_dir)

        # Re-run the package search now we've ensured there are package files
        # extant
        self.distribution.packages = ['%s.%s.%s' % (CONFIG.test_egg_namespace,
                                                    self.old_name, i)
                                      for i in find_packages('tests')]

        # Bin the build directory, this stops artifacts from the real package
        # getting in there
        self.execute(shutil.rmtree, (self.build_lib,),
                    "removing %s (and everything under it)" % self.build_lib)

        # Re-run the egg-info step, setting the option to include test options
        self.reinitialize_command('egg_info')
        self.ei_cmd = self.get_finalized_command('egg_info')
        self.ei_cmd.include_test_options = True
        self.ei_cmd.tag_build = None
        self.ei_cmd.egg_version = self.old_version
        self.ei_cmd.run()

        # Copy all the test files into the build directory and ensure they're
        # real packages
        for root, dirs, files in os.walk(self.test_dir):
            if '.svn' in dirs:
                dirs.remove('.svn')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            for f in files:
                f = os.path.join(root, f)
                self.execute(self._copy_file, (f, self.get_file_dest(f)),
                        "copying %s -> %s" % (f, self.get_file_dest(f)))

        self.create_ns_pkg_files(self.build_lib)

        pytest_cfg = os.path.join(self.dest_dir, 'pytest.ini')
        self.execute(self.create_pytest_config, (pytest_cfg,),
                     "creating pytest config at %s" % pytest_cfg)

        # Kick off a bdist_egg which will build the egg for us
        _bdist_egg.run(self)

        # Clean up the egg-info dir, pkg_resources finds it in source
        # checkouts and thinks the package is installed somewhere
        self.execute(shutil.rmtree, (self.egg_info,),
                    "removing %s (and everything under it)" % self.egg_info)
