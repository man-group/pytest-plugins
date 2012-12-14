from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.pyuninstall import pyuninstall

USAGE = """\
usage: %(script)s [options] package_name
   or: %(script)s --help
"""


def main(argv=None, **kw):
    run_setup_command(pyuninstall, usage=USAGE, argv=argv, **kw)

if __name__ == '__main__':
    main()
