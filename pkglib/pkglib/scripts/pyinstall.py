from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.pyinstall import pyinstall
from pkglib.setuptools.command.update import update

USAGE = """\
usage: %(script)s [options] requirement_or_url ...
   or: %(script)s --help
"""


def main(argv=None, **kw):
    run_setup_command(pyinstall,
                      usage=USAGE,
                      argv=argv,
                      # We need update here as well for the -U flag
                      cmdclass={
                          'pyinstall': pyinstall,
                          'update': update,
                      },
                      **kw)

if __name__ == '__main__':
    main()
