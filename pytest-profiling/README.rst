Pytest Profiling Plugin
=======================

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
