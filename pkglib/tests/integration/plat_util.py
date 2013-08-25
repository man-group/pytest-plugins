import os
import subprocess
import contextlib
import shutil

from os import path

from pkglib_testing import util
from pkglib.scripts import plat
from pkglib import manage


@contextlib.contextmanager
def restore_dir():
    dname = os.path.abspath(os.getcwd())
    (yield)
    os.chdir(dname)


@contextlib.contextmanager
def rmtree(dname):
    (yield)
    if os.path.isdir(dname):
        shutil.rmtree(dname)


class PkgVirtualEnv(util.TmpVirtualEnv):

    plat_script = (
        'import imp;'
        'm = imp.load_source("m", "%s");'
        'm.test_main()' % path.join(path.dirname(path.abspath(__file__)),
                                    "plat_main.py")
    )

    def __init__(self, *args, **kwargs):
        super(PkgVirtualEnv, self).__init__(*args, **kwargs)
        self.pip_ = self.virtualenv / "bin" / "pip"
        self.pyinstall_ = self.virtualenv / "bin" / "pyinstall"
        self.install_package('pkglib', installer='easy_install')

    def run(self, *args, **kwargs):
        kwargs = dict(kwargs)
        kwargs.setdefault("capture", True)
        with restore_dir():
            out = super(PkgVirtualEnv, self).run(*args, **kwargs)
        return out

    def plat(self, cmd, prompt_answer="N"):
        script = " ".join((self.python, "-c '%s'" % self.plat_script))
        if prompt_answer and prompt_answer[0].upper() == "Y":
            script += " --yes-on-prompt"
        lines = self.run(" ".join((script, "--debug", cmd))).split("\n")
        return lines

    def pip(self, cmd):
        cmd = " ".join([self.pip_, cmd])
        lines = self.run(cmd).split("\n")
        return lines

    def pyinstall(self, cmd):
        cmd = " ".join([self.pyinstall_, cmd])
        lines = self.run(cmd).split("\n")
        return lines
