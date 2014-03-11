from pkglib.setuptools.command.clean import clean
from pkglib.scripts import run_setup_command


def main(argv=None, **kw):
    if argv is None:
        argv = []
    run_setup_command(clean, argv=argv + ['--packages'], **kw)

if __name__ == '__main__':
    main()
