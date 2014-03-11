import pkglib.setuptools  # @UnusedImport # needed so that distutils.PyPIRCCommand is monkey patched # NOQA

from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.deploy import deploy as _deploy
from distutils.errors import DistutilsOptionError


USAGE = """\
usage: %(script)s [options] path_to_egg_file ...
   or: %(script)s [options] package==version ...
   or: %(script)s --help
"""


class deploy(_deploy):
    command_consumes_arguments = True

    def initialize_options(self):
        _deploy.initialize_options(self)
        self.args = []
        self.enabled = True  # enable since running as a stand-alone

    def finalize_options(self):
        _deploy.finalize_options(self)
        if len(self.args) != 1:
            raise DistutilsOptionError("Single argument expected: "
                                       "a path to an egg file, or "
                                       "a package requirement")
        self.egg_file = self.args[0]


def main(argv=None, **kw):
    """
    Deploys an egg or requirement to the configured install path.

    Parameters
    ----------
    egg_file : `string`
        path to egg file.
    """
    run_setup_command(deploy,
                      usage=USAGE,
                      argv=argv,
                      cmdclass={
                          'deploy': deploy,
                      },
                      **kw)


if __name__ == "__main__":
    main()
