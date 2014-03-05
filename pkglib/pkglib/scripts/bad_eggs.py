from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.bad_eggs import bad_eggs


def main():
    """
    Find eggs on PyPi that have bad permissions (contain files that are not group/other readable,
    or directories or files that should be executable but are not).
    """
    run_setup_command(bad_eggs)


if __name__ == "__main__":
    main()
