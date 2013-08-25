from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
from setuptools import find_packages

from pkglib import CONFIG, config

from base import CommandMixin

NAMESPACE_PACKAGE_INIT = """
__import__('pkg_resources').declare_namespace(__name__)
"""

# This is the name of the namespace package that the tests get based under.
# Eg: acme.foo ->  $(CONFIG.test_egg_namespace).acme.foo

# IMPORTANT: 
# Can't use just 'tests' for the namespace im afraid, there's some poorly
# written 3rd party stuff out there that pushes 'tests' into the ns (I'm
# looking at you PasteScript)
# Also any source checkouts steal the 'tests' n/s due to path ordering.


class test_egg(_bdist_egg, CommandMixin):
    """ Build an egg that just contains the test artifacts.
    """
    def finalize_options(self):
        from path import path

        # Where the tests are found
        self.test_dir = path.getcwd() / 'tests'

        # Where in the build tree they're going
        build_py = self.get_finalized_command('build_py')
        self.build_lib = path(build_py.build_lib)
        self.dest_dir = self.build_lib / CONFIG.test_egg_namespace / \
                            (self.distribution.get_name().replace('.', '/'))

        # This stops the regular bdist builder from triggering, allowing us to
        # craft our own package underneath the regular build tree
        self.skip_build = True

        # Adjust the package metadata to suit our test package
        self.old_name = self.distribution.metadata.name
        self.distribution.metadata.name = 'test.{}'.format(
                                           self.distribution.metadata.name)
        self.distribution.namespace_packages = (
            [CONFIG.test_egg_namespace] +
            ['{}.{}'.format(CONFIG.test_egg_namespace, i)
             for i in self.distribution.namespace_packages]
        )
        self.distribution.entry_points = {}

        # Set the install requirements to be the test requirements of the 
        # original, plus a direct pin to the original version.
        self.old_version = self.get_finalized_command('egg_info').egg_version
        self.distribution.install_requires = (
            self.distribution.tests_require +
            ['{}=={}'.format(self.old_name, self.old_version)]
        )
        _bdist_egg.finalize_options(self)

    def get_file_dest(self, filename):
        return self.dest_dir / (filename.split(self.test_dir + '/')[1])

    def _copy_file(self, src, dest):
        from path import path
        test_dir = dest.parent
        test_dir.makedirs_p()
        path.copyfile(src, dest)

    def create_init_files(self, top_dir):
        """
        Creates empty __init__.py files for all dirs under and including
        a given directory if they are missing.
        """
        if top_dir.isdir():
            for dirname in list(top_dir.walkdirs()) + [top_dir]:
                if '.svn' in dirname or '__pycache__' in dirname:
                    continue
                pkg_init = dirname / '__init__.py'
                if not pkg_init.isfile():
                    self.execute(pkg_init.write_text, ('',),
                                 "creating missing package file at {}"
                                 .format(pkg_init))

    def create_ns_pkg_files(self, top_dir):
        """
        Creates ns package files where needed, eg in:
        build/lib/tests
        build/lib/tests/acme
        """
        if top_dir.isdir():
            for dirname in list(top_dir.walkdirs()):
                if dirname.split(top_dir + '/')[1].replace('/', '.') in \
                    self.distribution.namespace_packages:
                    pkg_init = dirname / '__init__.py'
                    if not pkg_init.isfile():
                        self.execute(pkg_init.write_text,
                                     (NAMESPACE_PACKAGE_INIT,),
                                     "creating missing namespace package file "
                                     "at {}".format(pkg_init))

    def create_pytest_config(self, filename):
        """
        Extracts the pytest specific sections from setup.cfg and puts them into
        a separate config file in the build dir
        """
        parser = config.get_pkg_cfg_parser()
        [parser.remove_section(s) for s in parser.sections() if s != 'pytest']
        if parser.has_section('pytest'):
            with filename.open('wb') as fp:
                parser.write(fp)

    def run(self):
        self.create_init_files(self.test_dir)
        # Re-run the package search now we've ensured there are package files
        # extant in the distro
        self.distribution.packages = ['%s.%s.%s' % (CONFIG.test_egg_namespace,
                                                    self.old_name, i)
                                      for i in find_packages('tests')]

        # Bin the build directory, this stops artifacts from the real package
        # getting in there
        self.execute(self.build_lib.rmtree, (self.build_lib,),
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
        for filename in self.test_dir.walk():
            if (not filename.isfile()
                or '.svn' in filename
                or '__pycache__' in filename):
                continue
            self.execute(self._copy_file, (filename,
                                           self.get_file_dest(filename)),
                        "copying {} -> {}"
                        .format(filename, self.get_file_dest(filename)))
        self.create_ns_pkg_files(self.build_lib)

        pytest_cfg = self.dest_dir / 'pytest.ini'
        self.execute(self.create_pytest_config, (pytest_cfg,),
                     "creating pytest config at %s" % pytest_cfg)

        # Kick off a bdist_egg which will build the egg for us
        _bdist_egg.run(self)

        # Clean up the egg-info dir, pkg_resources finds it in source checkouts
        # and thinks the package is installed somewhere
        self.execute(self.egg_info.rmtree, (self.egg_info,),
                    "removing %s (and everything under it)" % self.egg_info)
