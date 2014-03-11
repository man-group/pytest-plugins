from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.clean import clean

USAGE = """\
usage: %(script)s [options]
   or: %(script)s --help
"""


def main(argv=None, **kw):
    run_setup_command(clean,
                      usage=USAGE,
                      argv=argv + '--tidy',
                      cmdclass={
                          'tidy': clean,
                      },
                      **kw)

if __name__ == '__main__':
    main()
