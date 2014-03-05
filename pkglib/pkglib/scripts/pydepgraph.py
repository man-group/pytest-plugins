from pkglib import config
from pkglib.setuptools.command.depgraph import depgraph
from pkglib.scripts import run_setup_command

USAGE = """\
usage: %(script)s [options] [package name] [package name] ...
   or: %(script)s --help
"""


def main(argv=None, **kw):
    # TODO: allow cmdline override of org config?
    config.setup_global_org_config()
    run_setup_command(depgraph, usage=USAGE, argv=argv, **kw)

if __name__ == '__main__':
    main()
