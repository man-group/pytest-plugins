import os
import subprocess
import sys
import textwrap

import pytest_virtualenv as venv


def check_member(name, ips):
    return name in ips


def test_installed_packages():
    with venv.VirtualEnv() as v:
        ips = v.installed_packages()
        assert len(ips) > 0
        check_member('pip', ips)
        check_member('virtualenv', ips)


def test_virtualenv_fixture_autodelete(monkeypatch, tmpdir):
    workspace = (tmpdir / 'tmp').mkdir()
    monkeypatch.setenv('WORKSPACE', workspace)
    testsuite = tmpdir.join('test.py')
    with testsuite.open('w') as fp:
        fp.write(textwrap.dedent(
        """
        def test(virtualenv):
            pass
        """))
    subprocess.check_call([sys.executable, '-m', 'pytest', str(testsuite)])
    assert os.listdir(str(workspace)) == []
