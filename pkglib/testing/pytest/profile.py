'''
Profiling plugin for pytest, with tabular and heat graph output.

Tests are profiled with cProfile_ and analysed with pstats_; heat graphs are
generated using gprof2dot_ and dot_.

.. _cProfile: http://docs.python.org/library/profile.html#module-cProfile
.. _pstats: http://docs.python.org/library/profile.html#pstats.Stats
.. _gprof2dot: http://code.google.com/p/jrfonseca/wiki/Gprof2Dot
.. _dot: http://www.graphviz.org/

Usage
-----

Once the enclosing package is installed into your virtualenv, the plugin
provides extra options to pytest::

    $ py.test --help
    ...
      Profiling:
        --profile           generate profiling information
        --profile-svg       generate profiling graph (using gprof2dot and dot
                            -Tsvg)

The ``--profile`` and ``profile-svg`` options can be combined with any other
option::

    $ py.test tests/unit/test_logging.py --profile
    ============================= test session starts ==============================
    platform linux2 -- Python 2.6.2 -- pytest-2.2.3
    collected 3 items

    tests/unit/test_logging.py ...
    Profiling (from prof/combined.prof):
    Fri Oct 26 11:05:00 2012    prof/combined.prof

             289 function calls (278 primitive calls) in 0.001 CPU seconds

       Ordered by: cumulative time
       List reduced from 61 to 20 due to restriction <20>

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            3    0.000    0.000    0.001    0.000 <string>:1(<module>)
          6/3    0.000    0.000    0.001    0.000 core.py:344(execute)
            3    0.000    0.000    0.001    0.000 python.py:63(pytest_pyfunc_call)
            1    0.000    0.000    0.001    0.001 test_logging.py:34(test_flushing)
            1    0.000    0.000    0.000    0.000 _startup.py:23(_flush)
            2    0.000    0.000    0.000    0.000 mock.py:979(__call__)
            2    0.000    0.000    0.000    0.000 mock.py:986(_mock_call)
            4    0.000    0.000    0.000    0.000 mock.py:923(_get_child_mock)
            6    0.000    0.000    0.000    0.000 mock.py:512(__new__)
            2    0.000    0.000    0.000    0.000 mock.py:601(__get_return_value)
            4    0.000    0.000    0.000    0.000 mock.py:695(__getattr__)
            6    0.000    0.000    0.000    0.000 mock.py:961(__init__)
        22/14    0.000    0.000    0.000    0.000 mock.py:794(__setattr__)
            6    0.000    0.000    0.000    0.000 core.py:356(getkwargs)
            6    0.000    0.000    0.000    0.000 mock.py:521(__init__)
            3    0.000    0.000    0.000    0.000 skipping.py:122(pytest_pyfunc_call)
            6    0.000    0.000    0.000    0.000 core.py:366(varnames)
            3    0.000    0.000    0.000    0.000 skipping.py:125(check_xfail_no_run)
            2    0.000    0.000    0.000    0.000 mock.py:866(assert_called_once_with)
            6    0.000    0.000    0.000    0.000 mock.py:645(__set_side_effect)



    =========================== 3 passed in 0.13 seconds ===========================

pstats files (one per test item) are retained for later analysis in ``prof``
directory, along with a ``combined.prof`` file::

    $ ls -1 prof/
    combined.prof
    test_app.prof
    test_flushing.prof
    test_import.prof

If the ``--profile-svg`` option is given, along with the prof files and tabular
output a svg file will be generated::

    $ py.test tests/unit/test_logging.py --profile-svg
    ...
    SVG profile in prof/combined.svg.

This is best viewed with a good svg viewer e.g. Chrome.

.. image:: ../_static/profile_combined.svg

'''

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
