from __future__ import absolute_import

import sys
import os
import cProfile
import pstats
import errno
from hashlib import md5

import six
import pytest

LARGE_FILENAME_HASH_LEN = 8


def clean_filename(s):
    forbidden_chars = set('/?<>\:*|"')
    return six.text_type("".join(c if c not in forbidden_chars and ord(c) < 127 else '_'
                                 for c in s))


class Profiling(object):
    """Profiling plugin for pytest."""
    svg = False
    svg_name = None
    profs = []
    combined = None
    svg_err = None
    dot_cmd = None
    gprof2dot_cmd = None

    def __init__(self, svg, dir):
        self.svg = svg
        self.dir = 'prof' if dir is None else dir[0]
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

                # A/ Legacy: python pipes: does not seem to work on windows targets :(
                # import pipes
                # t = pipes.Template()
                # t.append("{} -f pstats $IN".format(self.gprof2dot), "f-")
                # t.append("dot -Tsvg -o $OUT", "-f")
                # t.copy(self.combined, self.svg_name)

                # B/ A handcrafted POpen pipe actually seems to work on windows:
                from subprocess import Popen, PIPE

                # the 2 commands that we wish to execute
                gprof2dot_args = [self.gprof2dot, "-f", "pstats", self.combined]
                dot_args = ["dot", "-Tsvg", "-o", self.svg_name]
                self.dot_cmd = " ".join(dot_args)
                self.gprof2dot_cmd = " ".join(gprof2dot_args)

                # do it in 2 subprocesses, with a pipe in between
                pdot = Popen(dot_args, stdin=PIPE, shell=True)
                pgprof = Popen(gprof2dot_args, stdout=pdot.stdin, shell=True)
                (stdoutdata1, stderrdata1) = pgprof.communicate()
                (stdoutdata2, stderrdata2) = pdot.communicate()
                if stderrdata1 is not None or pgprof.poll() > 0:
                    # error: gprof2dot
                    self.svg_err = 1
                elif stderrdata2 is not None or pdot.poll() > 0:
                    # error: dot
                    self.svg_err = 2
                else:
                    # success
                    self.svg_err = 0

                # C/ Safest and most portable way is to simply write a temporary file and delete it afterwards
                # The lines below work perfectly, in case we wish to use this behaviour later
                #
                # from subprocess import Popen
                # self.tmp_file_name = "tmp"
                #
                # # gprof2dot -f pstats prof/combined.prof > prof/tmp
                # gprof2dot_args = [self.gprof2dot, "-f", "pstats", self.combined, ">", self.tmp_file_name]
                # self.gprof2dot_cmd = " ".join(gprof2dot_args)
                # p = Popen(gprof2dot_args, shell=True)
                # p.wait()
                # if os.path.exists(self.tmp_file_name):
                #     # dot -Tsvg -o prof/combined.svg prof/tmp
                #     dot_args = ["dot", "-Tsvg", "-o", self.svg_name, self.tmp_file_name]
                #     self.dot_cmd = " ".join(dot_args)
                #     p2 = Popen(dot_args, shell=True)
                #     p2.wait()
                #     if os.path.exists(self.svg_name):
                #         self.svg_err = 0  # SUCCESS
                #         os.remove(self.tmp_file_name)  # remove tmp file
                #     else:
                #         self.svg_err = 2  # error: dot
                # else:
                #     self.svg_err = 1  # error: gprof2dot

    def pytest_terminal_summary(self, terminalreporter):
        if self.combined:
            terminalreporter.write("Profiling (from {prof}):\n".format(prof=self.combined))
            pstats.Stats(self.combined, stream=terminalreporter).strip_dirs().sort_stats('cumulative').print_stats(20)
        if self.svg_name:
            if not self.svg_err:
                # 0 - SUCCESS
                terminalreporter.write("SVG profile created in {svg}.\n".format(svg=self.svg_name))
            else:
                if self.svg_err == 1:
                    # 1 - GPROF2DOT ERROR
                    terminalreporter.write("Error creating SVG profile in {svg}.\n"
                                           "Command failed: {cmd}".format(svg=self.svg_name, cmd=self.gprof2dot_cmd))
                elif self.svg_err == 2:
                    # 2 - DOT ERROR
                    terminalreporter.write("Error creating SVG profile in {svg}.\n"
                                           "Command succeeded: {cmd} \n"
                                           "Command failed: {cmd2}".format(svg=self.svg_name, cmd=self.gprof2dot_cmd,
                                                                           cmd2=self.dot_cmd))

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
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


def pytest_configure(config):
    """pytest_configure hook for profiling plugin"""
    profile_enable = any(config.getvalue(x) for x in ('profile', 'profile_svg'))
    if profile_enable:
        config.pluginmanager.register(Profiling(config.getvalue('profile_svg'),
                                                config.getvalue('pstats_dir')))
