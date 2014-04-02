""" Temporary directory fixtures
"""
import os
import tempfile
import shutil
import subprocess
import logging

from path import path

from pkglib_util.six import string_types
from pkglib_util import cmdline

from .. import util

log = logging.getLogger(__name__)


def pytest_funcarg__workspace(request):
    """ Function-scoped temporary workspace.
        Cleans up on exit.
    """
    return request.cached_setup(
        setup=Workspace,
        teardown=lambda p: p.teardown(),
        scope='function',
    )


class Workspace(object):
    """
    Creates a temp workspace, cleans up on teardown.
    See pkglib_testing.pytest.util for an example usage.
    Can also be used as a context manager.

    Attributes
    ----------
    workspace : `path.path`
        Path to the workspace directory.
    debug: `bool`
        If set to True, will print more debug when running subprocess commands.
    delete: `bool`
        If True, will always delete the workspace on teardown; if None, delete
        the workspace unless teardown occurs via an exception; if False, never
        delete the workspace on teardown.
    """
    debug = False
    delete = True

    def __init__(self, workspace=None, delete=None):
        self.delete = delete

        log.debug("")
        log.debug("=======================================================")
        if workspace is None:
            self.workspace = path(tempfile.mkdtemp(dir=util.get_base_tempdir()))
            log.debug("pkglib_testing created workspace %s" % self.workspace)

        else:
            self.workspace = workspace
            log.debug("pkglib_testing using workspace %s" % self.workspace)
        if 'DEBUG' in os.environ:
            self.debug = True
        if self.delete is not False:
            log.debug("This workspace will delete itself on teardown")
        log.debug("=======================================================")
        log.debug("")

    def __enter__(self):
        return self

    def __exit__(self, errtype, value, traceback):  # @UnusedVariable
        if self.delete is None:
            self.delete = (errtype is None)
        self.teardown()

    def __del__(self):
        self.teardown()

    def run(self, cmd, capture=False, check_rc=True, cd=None, shell=True, **kwargs):
        """
        Run a command relative to a given directory, defaulting to the workspace root

        Parameters
        ----------
        cmd : `str`
            Command string.
        capture : `bool`
            Capture and return output
        check_rc : `bool`
            Assert return code is zero
        cd : `str`
            Path to chdir to, defaults to workspace root
        """
        if isinstance(cmd, str):
            cmd = [cmd]
            shell = True
        if not cd:
            cd = self.workspace
        with cmdline.chdir(cd):
            log.debug("run: %s" % str(cmd))
            if capture:
                p = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
            else:
                p = subprocess.Popen(cmd, shell=shell, **kwargs)
            (out, _) = p.communicate()

            if out is not None and not isinstance(out, string_types):
                out = out.decode('utf-8')

            if self.debug and capture:
                log.debug("Stdout/stderr:")
                log.debug(out)

            if check_rc and p.returncode != 0:
                err = subprocess.CalledProcessError(p.returncode, cmd)
                err.output = out
                if capture and not self.debug:
                    log.debug("Stdout/stderr:")
                    log.debug(out)
                raise err

        return out

    def teardown(self):
        if not self.delete:
            return
        if os.path.isdir(self.workspace):
            log.debug("")
            log.debug("=======================================================")
            log.debug("pkglib_testing deleting workspace %s" % self.workspace)
            log.debug("=======================================================")
            log.debug("")
            shutil.rmtree(self.workspace)

    def create_pypirc(self, config):
        """
        Create a .pypirc file in the workspace

        Parameters
        ----------
        config : `ConfigParser.ConfigParser`
            config instance
        """
        f = os.path.join(self.workspace, '.pypirc')
        mode = os.O_WRONLY | os.O_CREAT
        perm = 0o600

        with os.fdopen(os.open(f, mode, perm), 'wt') as rc_file:
            config.write(rc_file)