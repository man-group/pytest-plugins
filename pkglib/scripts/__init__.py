import sys
import os

from setuptools import setup
from setuptools.dist import Distribution
import distutils.core

from pkglib import config


DEFAULT_USAGE = """\
usage: %(script)s [options]
   or: %(script)s --help
"""


def run_setup_command(command, cmdclass=None, usage=DEFAULT_USAGE, argv=None, **kw):
    """ Cribbed from distribute.setuptools.command.easy_install. Runs a
        setup command via an entry point.
    """
    # TODO: allow cmdline override of org config?
    config.setup_org_config()


    def gen_usage(script_name):
        script = os.path.basename(script_name)
        return usage % vars()

    def with_ei_usage(f):
        old_gen_usage = distutils.core.gen_usage
        try:
            distutils.core.gen_usage = gen_usage
            return f()
        finally:
            distutils.core.gen_usage = old_gen_usage

    class DistributionWithoutHelpCommands(Distribution):
        common_usage = command.description

        def _show_help(self, *args, **kw):
            with_ei_usage(lambda: Distribution._show_help(self, *args, **kw))

        def find_config_files(self):
            files = Distribution.find_config_files(self)
            if 'setup.cfg' in files:
                files.remove('setup.cfg')
            return files

    if argv is None:
        argv = sys.argv[1:]

    global_opts = []
    for l, s, _ in [i[:3] for i in Distribution.global_options]:
        global_opts += ['--%s' % l, '-%s' % s]

    args = [i for i in argv if i in global_opts] + \
           [command.__name__] + \
           [i for i in argv if i not in global_opts]

    if cmdclass is None:
        cmdclass = {command.__name__: command}

    with_ei_usage(lambda:
        setup(
            script_args=args,
            script_name=sys.argv[0],
            distclass=DistributionWithoutHelpCommands,
            cmdclass=cmdclass,
            **kw))
