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
        assert check_member("pip", ips)


def test_install_version_from_current():
    with venv.VirtualEnv() as v:
        v.install_package("flask", "1.1.1")
        v.install_package("virtualenv", version=venv.PackageVersion.CURRENT)
        v.install_package("pytest-virtualenv", version=venv.PackageVersion.CURRENT)
        out = v.run([
            v.python,
            "-c",
            """import pytest_virtualenv as venv
with venv.VirtualEnv() as v:
    v.install_package("flask", version=venv.PackageVersion.CURRENT)
    print("The Flask version is", v.installed_packages()["Flask"].version)

"""
        ], capture=True)
        assert "The Flask version is 1.1.1" in out.strip()


def test_install_egg_link_from_current(tmp_path):
    with open(tmp_path / "setup.py", "w") as fp:
        fp.write("""from setuptools import setup
setup(name="foo", version="1.2", description="none available", install_requires=["requests"], py_modules=["foo"])
""")
    with open(tmp_path / "foo.py", "w") as fp:
        fp.write('print("hello")')

    with venv.VirtualEnv() as v:
        v.install_package("pip")
        v.install_package("wheel")
        v.install_package("virtualenv", version=venv.PackageVersion.CURRENT)
        v.install_package("pytest-virtualenv", version=venv.PackageVersion.CURRENT)
        v.run([v.python, "-m", "pip", "install", "-e", str(tmp_path)])
        out = v.run([
            v.python,
            "-c",
            """import pytest_virtualenv as venv
with venv.VirtualEnv() as v:
    v.install_package("foo", version=venv.PackageVersion.CURRENT)
    print("The foo version is", v.installed_packages()["foo"].version)
    print("Requests installed:", "requests" in v.installed_packages())
"""
        ], capture=True)
        assert "The foo version is 1.2" in out
        assert "Requests installed: True"


def test_install_pinned_version():
    with venv.VirtualEnv() as v:
        v.install_package("flask", "1.1.1")
        assert v.installed_packages()["Flask"].version == "1.1.1"


def test_install_latest():
    with venv.VirtualEnv() as v:
        v.install_package("flask")
        assert v.installed_packages()["Flask"].version != "1.1.1"
