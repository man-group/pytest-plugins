import sys

import pkglib.setuptools  # @UnusedImport # needed so that distutils.PyPIRCCommand is monkey patched # NOQA

from pkglib.scripts import run_setup_command
from pkglib.setuptools.command.upload_egg import upload_egg


USAGE = """\
usage: %(script)s [options] path_to_egg_file ...
   or: %(script)s --help
"""


def main(*egg_files, **kw):
    """
    Uploads an egg file to PyPI package index.

    Parameters
    ----------
    egg_file : `string`
        path to egg file.
    """
    run_setup_command(upload_egg,
                      usage=USAGE,
                      argv=egg_files if egg_files else sys.argv[1:],
                      cmdclass={'upload_egg': upload_egg},
                      **kw)


if __name__ == "__main__":
    main()
