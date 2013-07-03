import os
import sys
import subprocess
from distutils import log
from distutils.errors import DistutilsOptionError

from setuptools import Command

from pkglib import CONFIG, config

from base import CommandMixin

HUDSON_XML_PYLINT = "pylint.xml"
HUDSON_XML_JUNIT = "junit.xml"
# This is here only for reference, the filename can be changed only in .coveragerc
HUDSON_XML_COVERAGE = "coverage.xml"


class test(Command, CommandMixin):
    """ Enable Py.test for setup.py commands """
    description = "Run tests via py.test. " \
                  "Extra arguments are passed to py.test, but must be " \
                  "surrounded  with escaped quotes, eg \\\"--extra-arg\\\""
    command_consumes_arguments = True

    user_options = [
        ("hudson", "H",
         "Run tests with Hudson metrics options. This is automatically set "
         "when ${BUILD_TAG} matches /^(hudson|jenkins)/"),
        ("pylint-options=", None,
         "PyLint command-line options, eg to disable certain warnings"),
        ("unit", 'u', "Run only unit tests under tests/unit"),
        ("integration", 'i',
         "Run only integration tests under tests/integration"),
        ("regression", 'r',
         "Run only regression tests under tests/regression"),
        ("file=", 'f', "Only run tests in the specified file/s"),
        ("doctest", 'd',
         "Run only doctests for python modules in this package"),
        ("subprocess", 'S', "Run tests in a subprocess."),
        ("pdb", None,
         "Run tests under pdb, will drop into the debugger on failure."),
        ("quiet", 'q', "Run tests quietly"),
        ("ignore", None, "Ignore tests matching this pattern"),
        ("no-pylint", None, "Disable pylint checking"),
        ("no-deps", 'N',
         "Disable resolving of test dependencies"),
        ("test-root", None,
         "Root directory for tests, defaults to all directories matching "
         "'{0}' under {1}".format(CONFIG.test_dirname, os.getcwd())),
    ]
    boolean_options = [
        'hudson',
        'unit',
        'integration',
        'regression',
        'doctest',
        'subprocess',
        'pdb',
        'quiet',
        'no-pylint',
        'no-deps',
    ]

    def initialize_options(self):
        self.hudson = False
        if os.environ.get('BUILD_TAG', '').startswith('hudson') or \
           os.environ.get('BUILD_TAG', '').startswith('jenkins'):
            self.hudson = True
        self.pylint_options = []
        self.all = True
        self.unit = False
        self.integration = False
        self.regression = False
        self.doctest = False
        self.args = None
        self.subprocess = False
        self.pdb = False
        self.quiet = False
        self.ignore = None
        self.no_pylint = False
        self.no_deps = False
        self.file = None
        self.test_root = []
        self.default_options = self.get_option_list()

    def finalize_options(self):
        # TODO: do this in a nicer fashion, so you dont have to quote things.
        # Strip quotes off of any trailing arguments, these will be
        # passed into pytest as extra args
        if self.args is None:
            self.args = []
        for i in range(len(self.args)):
            if self.args[i].startswith('"'):
                self.args[i] = self.args[i][1:]
            if self.args[i].endswith('"'):
                self.args[i] = self.args[i][:-1]

        if self.unit or self.integration or self.doctest or self.file or \
           self.regression:
            self.all = False

        if self.pylint_options:
            self.pylint_options = self.pylint_options.split()

        if not self.test_root:
            self.test_root = self.get_test_roots()
        else:
            self.test_root = [self.test_root]

    def get_test_roots(self):
        """ Find test directories, skipping nested dirs and anything marked
            to skip under [pytest]:norecursedirs
        """
        from path import path
        res = []
        no_recurse = []
        cfg = config.get_pkg_cfg_parser()
        if cfg.has_section('pytest') and \
           cfg.has_option('pytest', 'norecursedirs'):
            [no_recurse.extend(path.getcwd().glob(i)) for i in
             cfg.get('pytest', 'norecursedirs').split()]
            no_recurse = [i.abspath() for i in no_recurse]

        test_dirs = [i for i in
                     path.getcwd().walkdirs(CONFIG.test_dirname)]
        test_dirs.sort(key=len)
        for i in test_dirs:
            try:
                for j in res + no_recurse:
                    if i.startswith(j):
                        raise ValueError
            except ValueError:
                pass
            else:
                res.append(i)
        log.debug("Test roots: {0}".format(res))
        return res

    def get_options(self):
        """ Returns all the options and args this was initialized with.
            Used by test_egg to save away configured options when there's no
            setup.cfg to use.
        """
        return [i for i in self.get_option_list()
                if i not in self.default_options]

    def get_env(self):
        """ Returns shell env for use in subprocesses
        """
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(sys.path)
        return env

    def fetch_requirements(self):
        """ Download any missing requirements to local pkg dir.
            This will allow you to use anything that gets pulled in for
            by tests_require as well, eg pytest, pytest-cov etc.
        """
        run_requirements = set(self.distribution.install_requires +
                               self.distribution.tests_require)

        # We always need Py.Test with the coverage module.
        run_requirements.add('pytest-cov')

        # We need pylint if we're running in Hudson mode
        if CONFIG.test_linter_package and self.hudson and not self.no_pylint:
            run_requirements.add(CONFIG.test_linter_package)

        self.fetch_build_eggs(run_requirements, prefer_final=False,
                              use_existing=True)

    def run_pytest(self, args, use_subprocess):
        """ Run py.test with the given arguments.

            Parameters
            ----------
            args : `list`
                Command-line args
            use_subprocess : `bool`
                Run in a subprocess. If false, process will exit along
                with Py.test
        """
        log.info("Pytest args: %s" % ' '.join(args))
        import pytest
        if use_subprocess:
            log.info("Running in a subprocess")
            cmd = [sys.executable, pytest.__file__] + args
            log.debug(cmd)
            p = subprocess.Popen(cmd, env=self.get_env())
            p.communicate()
            rc = p.returncode
            if rc != 0:
                raise SystemExit(rc)
        else:
            raise SystemExit(pytest.main(args=args))

    def run_pylint(self):
        """ Run our configured linter over the code This will only be executed
            in Hudson mode.
        """
        cmd = [CONFIG.test_linter] + self.pylint_options
        cmd += self.get_package_dirs()

        print "PyLint XML written to file %s" % HUDSON_XML_PYLINT
        with open(HUDSON_XML_PYLINT, 'w') as f:
            (stdout, stderr) = subprocess.Popen(
                cmd, env=self.get_env(), stdout=subprocess.PIPE).communicate()
            if stdout:
                for line in stdout:
                    f.write(line)
            else:
                print ("No output from pylint.  stdout={0}, stderr={1}"
                       .format(stdout, stderr))

    def get_package_dirs(self):
        """ Returns the minimum set of directories containing our code
        """
        res = []
        pkg_dirs = self.distribution.packages[:]
        pkg_dirs.sort(key=len)
        for i in pkg_dirs:
            try:
                for j in res:
                    if i.startswith(j):
                        raise ValueError
            except ValueError:
                pass
            else:
                res.append(i)
        return set(res)

    def get_args(self):
        """ Build args for py.test
        """
        # Default py.test arguments can be passed in from the cmdline
        if self.args:
            pytest_args = self.args
        else:
            pytest_args = []

        if not self.quiet:
            pytest_args += ['--verbose']

        # Set up args for running doctests, this excludes coverage
        doctest_args = list(self.get_package_dirs()) + pytest_args

        # Choose packages for coverage. This is all the ones found by the distutils
        # find_packages, excluding namespace packages.
        pytest_args += ['--cov=%s' % p for p in self.distribution.packages  if
                                    p not in self.distribution.namespace_packages]

        for dirname in self.get_package_dirs():
            doctest_args += ['--doctest-modules', dirname]

        if self.hudson:
            pytest_args += ['--cov-report=xml', '--junitxml=%s' % HUDSON_XML_JUNIT]
        else:
            pytest_args += ['--cov-report=term']

        if self.pdb:
            pytest_args += ['--pdb', '-s', '-v']

        if self.ignore:
            pytest_args += ['--ignore', self.ignore]
            doctest_args += ['--ignore', self.ignore]

        # Choose tests to run
        test_dirs = []
        if self.all:
            test_dirs = self.test_root
        else:
            if self.unit:
                test_dirs.extend([i / 'unit' for i in self.test_root])
            if self.integration:
                test_dirs.extend([i / 'integration' for i in self.test_root])
            if self.regression:
                test_dirs.extend([i / 'regression' for i in self.test_root])

        if self.file:
            pytest_args += self.file.split()
        else:
            extant_test_dirs = [i for i in test_dirs if i.isdir()]
            if not extant_test_dirs:
                msg = "Can't find any test directories, tried {0}".format(
                      ','.join(test_dirs))
                raise DistutilsOptionError(msg)
            pytest_args.extend(extant_test_dirs)

        return pytest_args, doctest_args

    def run(self):
        """ Main run function
        """
        if not self.no_deps:
            self.execute(self.fetch_requirements, [], "Fetching test requirements")

        pytest_args, doctest_args = self.get_args()

        try:
            # Run doctests first.
            if self.doctest:
                # Always run doctests in a subprocess. This stops them hiding coverage results of imports.
                self.execute(self.run_pytest, (doctest_args, True), "Running doctests")

            # Now run the regular tests
            if self.all or self.unit or self.integration or self.file or self.regression:
                self.execute(self.run_pytest, (pytest_args, self.subprocess), "Running tests")
        finally:
            if self.hudson and not self.no_pylint:
                self.execute(self.run_pylint, [], "Running pylint")
