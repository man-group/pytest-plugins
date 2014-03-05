from pkglib import config
from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.tidy import tidy

USAGE = """\
usage: %(script)s [options]
   or: %(script)s --help
"""


def main(argv=None, **kw):
    config.setup_global_org_config()
    run_setup_command(tidy,
                      usage=USAGE,
                      argv=argv,
                      cmdclass={
                          'tidy': tidy,
                      },
                      **kw)

if __name__ == '__main__':
    main()
