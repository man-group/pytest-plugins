import sys
import os
from pkglib.setuptools.command.test import test
from distutils import log


class ext_gcov_test(test):
    """
    Run tests (as per the 'test' command) with gcov on Python extensions to generate
    Cobertura gcov/coverage.xml.
    This command depends on 'build' and 'build_ext_static_interpreter' commands; the latter is because
    gcov doesn't work on dynamically loaded modules, so we have to statically link the extensions as
    builtin modules.
    """
    description = "Run test coverage for Python extensions"
    user_options = test.user_options + [
        ("gcov-base", None, "Base directory for gcov output, defaults to %s/gcov" % os.getcwd()),
        ("gcov-coverage-file", None, "coverage.xml file, default is {gcov-base}/coverage.xml"),
    ]

    def initialize_options(self):
        from path import path
        self.gcov_base = path.getcwd() / 'gcov'
        self.gcov_coverage_file = None
        super(ext_gcov_test, self).initialize_options()

    def finalize_options(self):
        super(ext_gcov_test, self).finalize_options()
        self.gcov_coverage_file = self.gcov_coverage_file or (self.gcov_base / "coverage.xml")

    def run(self):
        self.fetch_build_eggs(["gcovr"])
        self.execute(self.clean_gcov_base, (), "Cleaning gcov directory")
        interpreter_filename, uses_cython = self.build_gcov_interpreter()
        log.info("built interpreter: {0}".format(interpreter_filename))

        self.execute(self.fetch_requirements, [], "Fetching test requirements")
        pytest_args, doctest_args = self.get_args()
        if self.doctest:
            self.execute(self.run_gcov_pytest, (doctest_args, interpreter_filename), "Running doctests")
        if self.all or self.unit or self.integration:
            self.execute(self.run_gcov_pytest, (pytest_args, interpreter_filename), "Running tests")

        if uses_cython:     # cython emits #line references to 'cython_utility' that confuse gcovr
            log.info("Creating dummy cython_utility for gcovr")
            from path import path
            open(path.getcwd() / 'cython_utility', 'w').close()

        import re
        gcovr_args = [os.path.join(sys.exec_prefix, "bin", "gcovr"), self.gcov_base, "--root=.",
                      "--exclude=" + re.escape(self.gcov_base) + "/.*",
                      "--exclude=cython_utility",
                      "--exclude=.*\.egg/.*"]
        self.spawn(gcovr_args)  # tabular to stdout
        self.spawn(gcovr_args + ["--xml", "--output=" + self.gcov_coverage_file])

    def clean_gcov_base(self):
        import shutil
        if os.path.isdir(self.gcov_base):
            shutil.rmtree(self.gcov_base)

    def run_gcov_pytest(self, args, interpreter):
        log.info("Pytest args: %s" % ' '.join(args))
        import pytest
        log.info("Running {0}".format(interpreter))
        cmd = [interpreter, pytest.__file__] + args
        log.debug(cmd)
        import subprocess
        p = subprocess.Popen(cmd, env=self.get_env())
        p.communicate()

    def build_gcov_interpreter(self):
        build = self.reinitialize_command('build')
        build.build_base = str(self.gcov_base)
        esi = self.reinitialize_command('build_ext_static_interpreter')
        esi.extra_compile_args += " -O0 -ggdb3 --coverage"
        esi.extra_link_args += " --coverage"
        esi.interpreter_filename = self.gcov_base / "gcov_interpreter"
        esi = self.get_finalized_command('build_ext_static_interpreter')
        uses_cython = esi.uses_cython()     # have to check before run()
        esi.run()
        return esi.interpreter_filename, uses_cython
