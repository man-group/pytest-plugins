""" General utility module
"""
import os
import sys

# ---------- Methods -------------------------#


def get_base_tempdir():
    """ Returns an appropriate dir to pass into
        tempfile.mkdtemp(dir=xxx) or similar.
    """
    return os.getenv('WORKSPACE')


def get_real_python_executable():
    real_prefix = getattr(sys, "real_prefix", None)
    if not real_prefix:
        return sys.executable

    executable_name = os.path.basename(sys.executable)
    bindir = os.path.join(real_prefix, "bin")
    if not os.path.isdir(bindir):
        print("Unable to access bin directory of original Python "
              "installation at: %s" % bindir)
        return sys.executable

    executable = os.path.join(bindir, executable_name)
    if not os.path.exists(executable):
        executable = None
        for f in os.listdir(bindir):
            if not f.endswith("ython"):
                continue

            f = os.path.join(bindir, f)
            if os.path.isfile(f):
                executable = f
                break

        if not executable:
            print("Unable to locate a valid Python executable of original "
                  "Python installation at: %s" % bindir)
            executable = sys.executable

    return executable


