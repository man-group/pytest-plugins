import os
import sys
import subprocess
import glob
from distutils import log
from distutils.errors import DistutilsOptionError

from setuptools import Command

from pkglib import CONFIG
from pkglib.config import parse

from base import CommandMixin, fetch_build_eggs

HUDSON_XML_PYLINT = "pylint.xml"
HUDSON_XML_JUNIT = "junit.xml"
# This is here only for reference, the filename can be changed only in .coveragerc
HUDSON_XML_COVERAGE = "coverage.xml"

# These are trailing arguments passed directly to pytest.
trailing_args = []


def gather_trailing_args():
    """ Gather trailing arguments for pytest, this can't be done using setuptools' api """
    global trailing_args
    if 'test' in sys.argv:
        test_args = sys.argv[sys.argv.index('test') + 1:]
        test_switches = []
        for (double, single, _) in test.user_options:
            test_switches.append('--' + double.split('=')[0])
            if single:
                test_switches.append('-' + single)

        for idx, arg in enumerate(test_args):
            if arg not in test_switches:
                trailing_args = test_args[idx:]
                sys.argv = sys.argv[:-len(trailing_args)]
                break
        # print("Py.test switches: {}".format(test.trailing_args))


class test(Command, CommandMixin):
    """ Enable Py.test for setup.py commands """
    description = "Run tests via py.test. " \
                  "Trailing arguments are passed directly to py.test"
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
        res = []
        no_recurse = []
        cfg = parse.get_pkg_cfg_parser()
        if cfg.has_section('pytest') and \
           cfg.has_option('pytest', 'norecursedirs'):
            [no_recurse.extend(glob.glob(os.path.join(os.getcwd(), i)))
             for i in cfg.get('pytest', 'norecursedirs').split()]
            no_recurse = [os.path.abspath(i) for i in no_recurse]

        test_dirs = []
        for (dirpath, dirnames, _) in os.walk(os.getcwd()):
            if CONFIG.test_dirname in dirnames:
                test_dirs.append(os.path.join(dirpath, CONFIG.test_dirname))
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
        all_requirements = self.get_requirements(extras=True, test=True)

        # We always need Py.Test with the coverage module.
        all_requirements.add('pytest')
        all_requirements.add('pytest-cov')

        # We need pylint if we're running in Hudson mode
        if CONFIG.test_linter_package and self.hudson and not self.no_pylint:
            all_requirements.add(CONFIG.test_linter_package)

        fetch_build_eggs(list(all_requirements), dist=self.distribution,
                         prefer_final=False, use_existing=True, add_to_env=True)

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

    def write_pylint_results(self, pylint_results):
        """ Saves PyLint warnings/errors into one or possibly multiple file(s).
            By default, PyLint is executed from the base package directory
            (directory where 'setup.py' file is located). Therefore all paths
            generated by PyLint will be relative to the base directory.

            In situations when 'setup.py' is invoked from a non-base directory
            an additional PyLint result file will be written to the original
            invocation location, with paths amended accordingly.

            An additional PyLint file is also written to the root of the
            job workspace if tests are run in a CI mode (i.e. when self.hudson
            is set to True).

            Parameters
            ----------
            pylint_results : `list<str>'
                output from PyLint line by line
        """
        cwd = os.path.abspath(os.getcwd())
        original_cwd = getattr(self.distribution, "original_cwd", cwd)
        output_files = set([])

        if self.hudson:
            workspace = os.environ.get("WORKSPACE", original_cwd)
            output_files.add(os.path.join(workspace, HUDSON_XML_PYLINT))
        else:
            output_files.add(os.path.join(cwd, HUDSON_XML_PYLINT))
            output_files.add(os.path.join(original_cwd, HUDSON_XML_PYLINT))

        def write_pylint_results_to_file(errors, out_file):
            output_dir = os.path.dirname(out_file)
            prefix = ("" if cwd == output_dir else
                      (os.path.relpath(cwd, output_dir) + os.path.sep))

            with open(out_file, 'w') as f:
                for line in errors:
                    f.write(prefix + line + '\n')

        for pylint_file in output_files:
            try:
                write_pylint_results_to_file(pylint_results, pylint_file)
                print("PyLint XML written to file: %s" % pylint_file)
            except OSError as e:
                print("Error writing PyLint XML to: " % pylint_file)
                print(str(e))

    def run_pylint(self):
        """ Run our configured linter over the code. This will only
        be executed in Hudson mode. This is a bit convoluted as the linter might
        only be installed into the local pkg dir rather than site-packages.
        """
        cmd = [CONFIG.test_linter] + self.pylint_options
        cmd += list(self.get_package_dirs())
        pylint_proc = subprocess.Popen(cmd, env=self.get_env(),
                                       stdout=subprocess.PIPE)
        (stdout, stderr) = pylint_proc.communicate()

        if stdout:
            if not isinstance(stdout, str):
                stdout = stdout.decode('utf-8')
            pylint_results = [l for l in stdout.splitlines() if l]
        else:
            pylint_results = []

        if pylint_proc.returncode:
            print("Error running PyLint (exit code={0})\n"
                  "stdout: {0}\nstderr: {1}".format(pylint_proc.returncode,
                                                    stdout, stderr))
        elif not pylint_results:
            print("PyLint did not find any issues with the source code")
        else:
            print("PyLint detected [{0}] violation(s)"
                  "".format(len(pylint_results)))

        self.write_pylint_results(pylint_results)

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
        pytest_args = trailing_args[:]

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
                test_dirs.extend([os.path.join(i, 'unit') for i in self.test_root])
            if self.integration:
                test_dirs.extend([os.path.join(i, 'integration') for i in self.test_root])
            if self.regression:
                test_dirs.extend([os.path.join(i, 'regression') for i in self.test_root])

        if self.file:
            pytest_args += self.file.split()
        else:
            extant_test_dirs = [i for i in test_dirs if os.path.isdir(i)]
            if not extant_test_dirs:
                msg = "Can't find any test directories, tried {0}".format(
                      ','.join(test_dirs))
                raise DistutilsOptionError(msg)
            pytest_args.extend(extant_test_dirs)

        return pytest_args, doctest_args

    def run(self):
        """ Main run function
        """
        self.execute(self.fetch_requirements, [], "Fetching test requirements")

        pytest_args, doctest_args = self.get_args()

        # In some weird cases sys.stdout gets closed by pytest.main
        # It must be re-opened for PyLint run, so save it's details now
        stdout_fileno = sys.stdout.fileno()
        stdout_cl = sys.stdout.__class__

        try:
            # Run doctests first.
            if self.doctest:
                # Always run doctests in a subprocess. This stops them hiding
                # coverage results of imports.
                self.execute(self.run_pytest, (doctest_args, True),
                             "Running doctests")

            # Now run the regular tests
            if any((self.all, self.unit, self.integration, self.file,
                    self.regression)):
                self.execute(self.run_pytest, (pytest_args, self.subprocess),
                             "Running tests")
        finally:

            if sys.stdout.closed:
                stream = os.fdopen(stdout_fileno, 'wb', 0)
                sys.stdout = stdout_cl(stream)

            if self.hudson and not self.no_pylint:
                self.execute(self.run_pylint, [], "Running PyLint")
