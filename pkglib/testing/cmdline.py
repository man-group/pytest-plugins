"""
        Testing tools for running cmdline methods
"""
import sys
from contextlib import contextmanager


@contextmanager
def _save_argv():
    args = sys.argv[:]
    yield
    sys.argv = args


def run_as_main(fn, *args):
    """ Run a given function as if it was the
    system entry point, eg for testing scripts.

    Eg::

        from scripts.Foo import main

        run_as_main(main, 'foo','bar')

    This is equivalent to ``Foo foo bar``, assuming
    ``scripts.Foo.main`` is registered as an entry point.
    """
    with _save_argv():
        print "run_as_main: %s" % str(args)
        sys.argv = ['progname'] + list(args)
        fn()
