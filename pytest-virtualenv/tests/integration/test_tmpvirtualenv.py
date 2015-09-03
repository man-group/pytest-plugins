import pytest_virtualenv as venv


def check_member(name, ips):
    return name in ips


def test_installed_packages():
    with venv.VirtualEnv() as v:
        ips = v.installed_packages()
        assert len(ips) > 0
        check_member('pip', ips)
        check_member('virtualenv', ips)
