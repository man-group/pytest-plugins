from __future__ import absolute_import

import pytest
import os
import cProfile
import pstats
import pipes


class Profiling(object):
    """Profiling plugin for pytest."""
    svg = False
    svg_name = None
    profs = []
    combined = None

    def __init__(self, svg):
        self.svg = svg
        self.profs = []

    def pytest_sessionstart(self, session):  # @UnusedVariable
        try:
            os.makedirs("prof")
        except OSError:
            pass

    def pytest_sessionfinish(self, session, exitstatus):  # @UnusedVariable
        if self.profs:
            combined = pstats.Stats(self.profs[0])
            for prof in self.profs[1:]:
                combined.add(prof)
            self.combined = os.path.join("prof", "combined.prof")
            combined.dump_stats(self.combined)
            if self.svg:
                self.svg_name = os.path.join("prof", "combined.svg")
                t = pipes.Template()
                t.append("gprof2dot -f pstats $IN", "f-")
                t.append("dot -Tsvg -o $OUT", "-f")
                t.copy(self.combined, self.svg_name)

    def pytest_terminal_summary(self, terminalreporter):
        if self.combined:
            terminalreporter.write("Profiling (from {prof}):\n".format(prof=self.combined))
            pstats.Stats(self.combined, stream=terminalreporter).strip_dirs().sort_stats('cumulative').print_stats(20)
        if self.svg_name:
            terminalreporter.write("SVG profile in {svg}.\n".format(svg=self.svg_name))

    @pytest.mark.tryfirst
    def pytest_pyfunc_call(self, __multicall__, pyfuncitem):
        """Hook into pytest_pyfunc_call; marked as a tryfirst hook so that we
        can call everyone else inside `cProfile.runctx`.
        """
        prof = os.path.join("prof", pyfuncitem.name + ".prof")
        cProfile.runctx("fn()", globals(), dict(fn=__multicall__.execute), filename=prof)
        self.profs.append(prof)


def pytest_addoption(parser):
    """pytest_addoption hook for profiling plugin"""
    group = parser.getgroup('Profiling')
    group.addoption("--profile", action="store_true",
                    help="generate profiling information")
    group.addoption("--profile-svg", action="store_true",
                    help="generate profiling graph (using gprof2dot and dot -Tsvg)")


def pytest_configure(config):
    """pytest_configure hook for profiling plugin"""
    profile_enable = any(config.getvalue(x) for x in ('profile', 'profile_svg'))
    if profile_enable:
        config.pluginmanager.register(Profiling(config.getvalue('profile_svg')))
