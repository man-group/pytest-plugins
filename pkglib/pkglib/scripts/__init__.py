import sys
import os
from contextlib import contextmanager

import distutils.core
from setuptools import setup

from pkglib.setuptools.dist import Distribution
from pkglib.config import org


DEFAULT_USAGE = """\
usage: %(script)s [options]
   or: %(script)s --help
"""


def _create_args(argv, command):
    if argv is None:
        argv = sys.argv[1:]

    global_opts = []
    for l, s, _ in [i[:3] for i in Distribution.global_options]:
        global_opts += ['--%s' % l, '-%s' % s]

    return [i for i in argv if i in global_opts] + \
           [command.__name__] + \
           [i for i in argv if i not in global_opts]


@contextmanager
def ei_usage(usage):
    def gen_usage(script_name):
        script = os.path.basename(script_name)
        return usage % {'script': script}
    old_gen_usage = distutils.core.gen_usage
    distutils.core.gen_usage = gen_usage
    try:
        yield
    finally:
        distutils.core.gen_usage = old_gen_usage


def run_setup_command(command, cmdclass=None, usage=DEFAULT_USAGE, argv=None,
                      **kw):
    """ Cribbed from distribute.setuptools.command.easy_install. Runs a
        setup command via an entry point.
    """
    org.setup_global_org_config()

    class DistributionWithoutHelpCommands(Distribution):
        common_usage = command.description

        def _show_help(self, *args, **kw):
            with ei_usage(usage):
                Distribution._show_help(self, *args, **kw)

        def find_config_files(self):
            files = Distribution.find_config_files(self)
            if 'setup.cfg' in files:
                files.remove('setup.cfg')
            return files

    args = _create_args(argv, command)

    if cmdclass is None:
        cmdclass = {command.__name__: command}

    with ei_usage(usage):
        setup(
            script_args=args,
            script_name=sys.argv[0],
            distclass=DistributionWithoutHelpCommands,
            cmdclass=cmdclass,
            **kw)
