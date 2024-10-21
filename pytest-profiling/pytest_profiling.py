"""pytest: avoid already-imported warning: PYTEST_DONT_REWRITE."""

from __future__ import absolute_import

import sys
import os
import cProfile
import pstats
import errno
from hashlib import md5
import subprocess

import six
import pytest

LARGE_FILENAME_HASH_LEN = 8


def clean_filename(s):
    forbidden_chars = set(r'/?<>\:*|"')
    return six.text_type("".join(c if c not in forbidden_chars and ord(c) < 127 else '_'
                                 for c in s))


class Profiling(object):
    """Profiling plugin for pytest."""
    svg = False
    svg_name = None
    profs = []
    stripdirs = False
    combined = None
    err_msg = None
    exit_code = None
    dot_cmd = None
    gprof2dot_cmd = None

    def __init__(self, svg, dir=None, element_number=20, stripdirs=False):
        self.svg = svg
        self.dir = 'prof' if dir is None else dir[0]
        self.stripdirs = stripdirs
        self.element_number = element_number
        self.profs = []
        self.gprof2dot = os.path.abspath(os.path.join(os.path.dirname(sys.executable), 'gprof2dot'))
        if not os.path.isfile(self.gprof2dot):
            # Can't see gprof in the local bin dir, we'll just have to hope it's on the path somewhere
            self.gprof2dot = 'gprof2dot'

    def pytest_sessionstart(self, session):  # @UnusedVariable
        try:
            os.makedirs(self.dir)
        except OSError:
            pass

    def pytest_sessionfinish(self, session, exitstatus):  # @UnusedVariable
        if self.profs:
            combined = pstats.Stats(self.profs[0])
            for prof in self.profs[1:]:
                combined.add(prof)
            self.combined = os.path.abspath(os.path.join(self.dir, "combined.prof"))
            combined.dump_stats(self.combined)
            if self.svg:
                self.svg_name = os.path.abspath(os.path.join(self.dir, "combined.svg"))

                # convert file <self.combined> into file <self.svg_name> using a pipe of gprof2dot | dot
                # gprof2dot -f pstats prof/combined.prof | dot -Tsvg -o prof/combined.svg

                # the 2 commands that we wish to execute
                gprof2dot_args = [self.gprof2dot, "-f", "pstats", self.combined]
                dot_args = ["dot", "-Tsvg", "-o", self.svg_name]
                self.dot_cmd = " ".join(dot_args)
                self.gprof2dot_cmd = " ".join(gprof2dot_args)

                # A handcrafted Popen pipe actually seems to work on both windows and unix:
                # do it in 2 subprocesses, with a pipe in between
                try:
                    with subprocess.Popen(gprof2dot_args, stdout=subprocess.PIPE) as pgprof:
                        with subprocess.Popen(
                            dot_args, stdin=pgprof.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        ) as pdot:
                            pgprof.stdout.close()  # Allow pgprof to receive a SIGPIPE if pdot exits
                            stdout, stderr = pdot.communicate()
                            if pgprof.returncode != 0:
                                self.err_msg = f"gprof2dot failed with return code {pgprof.returncode}"
                                self.exit_code = pgprof.returncode
                            if pdot.returncode != 0:
                                self.err_msg = f"dot failed with return code {pdot.returncode}: {stderr.decode()}"
                                self.exit_code = pdot.returncode
                            else:
                                self.exit_code = 0

                except subprocess.CalledProcessError as e:
                    self.err_msg = stderr.decode()
                    self.exit_code = 1
                except FileNotFoundError as e:
                    self.err_msg = str(e)
                    self.exit_code = 1

    def pytest_terminal_summary(self, terminalreporter):
        if self.combined:
            terminalreporter.write("Profiling (from {prof}):\n".format(prof=self.combined))
            stats = pstats.Stats(self.combined, stream=terminalreporter)
            if self.stripdirs:
                stats.strip_dirs()
            stats.sort_stats('cumulative').print_stats(self.element_number)
        if self.svg_name:
            if not self.exit_code:
                # 0 - SUCCESS
                terminalreporter.write("SVG profile created in {svg}.\n".format(svg=self.svg_name))
            else:
                terminalreporter.write(
                    f"Error when executing: {self.gprof2dot_cmd} | {self.dot_cmd} \n"
                    f"Error message={self.err_msg}"
                )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        prof_filename = os.path.abspath(os.path.join(self.dir, clean_filename(item.name) + ".prof"))
        try:
            os.makedirs(os.path.dirname(prof_filename))
        except OSError:
            pass
        prof = cProfile.Profile()
        prof.enable()
        yield
        prof.disable()
        try:
            prof.dump_stats(prof_filename)
        except EnvironmentError as err:
            if err.errno != errno.ENAMETOOLONG:
                raise

            if len(item.name) < LARGE_FILENAME_HASH_LEN:
                raise

            hash_str = md5(item.name.encode('utf-8')).hexdigest()[:LARGE_FILENAME_HASH_LEN]
            prof_filename = os.path.join(self.dir, hash_str + ".prof")
            prof.dump_stats(prof_filename)
        self.profs.append(prof_filename)


def pytest_addoption(parser):
    """pytest_addoption hook for profiling plugin"""
    group = parser.getgroup('Profiling')
    group.addoption("--profile", action="store_true",
                    help="generate profiling information")
    group.addoption("--profile-svg", action="store_true",
                    help="generate profiling graph (using gprof2dot and dot -Tsvg)")
    group.addoption("--pstats-dir", nargs=1,
                    help="configure the dump directory of profile data files")
    group.addoption("--element-number", action="store", type=int, default=20,
                    help="defines how many elements will display in a result")
    group.addoption("--strip-dirs", action="store_true",
                    help="configure to show/hide the leading path information from file names")


def pytest_configure(config):
    """pytest_configure hook for profiling plugin"""
    profile_enable = any(config.getvalue(x) for x in ('profile', 'profile_svg'))
    if profile_enable:
        config.pluginmanager.register(Profiling(config.getvalue('profile_svg'),
                                                config.getvalue('pstats_dir'),
                                                element_number=config.getvalue('element_number'),
                                                stripdirs=config.getvalue('strip_dirs')))
