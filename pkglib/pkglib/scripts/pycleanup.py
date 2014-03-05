from pkglib import config
from pkglib.setuptools.command.cleanup import cleanup
from pkglib.scripts import run_setup_command


def main(argv=None, **kw):
    # TODO: allow cmdline override of org config?
    config.setup_global_org_config()
    run_setup_command(cleanup, argv=argv, **kw)

if __name__ == '__main__':
    main()
