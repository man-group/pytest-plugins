import subprocess
import sys


def test_workspace_run_displays_output_on_failure():
    p = subprocess.Popen([sys.executable, '-c', """import logging
logging.basicConfig(level=logging.DEBUG)
from subprocess import CalledProcessError
from pytest_shutil.workspace import Workspace
try:
    Workspace().run('echo stdout; echo stderr >&2; false', capture=True)
except CalledProcessError:
    pass
else:
    raise RuntimeError("did not raise")
"""], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0]
    assert p.returncode == 0
    assert 'stdout\n'.encode('utf-8') in out
    assert 'stderr\n'.encode('utf-8') in out
