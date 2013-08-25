import mock

import pkglib_testing.util as util


def check_member(name, ips):
     return name in ips


def test_installed_packages():
     with util.TmpVirtualEnv() as v:
         ips = v.installed_packages()
         assert len(ips) > 0
         check_member('pip', ips)
         check_member('virtualenv', ips)
