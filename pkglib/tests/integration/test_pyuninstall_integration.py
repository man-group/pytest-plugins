"""
Tests covering the pyuninstall command
"""
import os
import pytest

from pkglib_testing.util import PkgTemplate, create_package_from_template as pkg_t
from test_pyinstall_integration import _dist_inhouse_eggs, USE_EGG_CACHE_VALUES


HERE = os.getcwd()


def _get_bin_cmd(env, cmd, arg, use_abs_python=True):
    prefix = (env.python + " ") if use_abs_python else ""
    return "%s%s/bin/%s -v %s" % (prefix, env.virtualenv, cmd, arg)


def _pyinstall(env, arg, *args, **kwargs):
    return env.run(_get_bin_cmd(env, "pyinstall", arg), *args, **kwargs)


def _pyuninstall(env, arg, *args, **kwargs):
    return env.run(_get_bin_cmd(env, "pyuninstall", arg), *args, **kwargs)


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_uninstall_egg_package(pytestconfig, simple_http_test_server, use_egg_cache):
    """ Creates template, runs pyinstall the pyuninstall"""
    with PkgTemplate(name='acme.foo') as pkg:
        pkg_t(pkg, "acme.bar", dev=False, metadata=dict(name="acme.bar", version="1.0"))
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _pyinstall(pkg, "-i %s acme.bar" % simple_http_test_server.uri)
        assert "acme.bar" in pkg.installed_packages()

        _pyuninstall(pkg, "--yes  acme.bar")
        assert "acme.bar" not in pkg.installed_packages()
