"""
Tests covering dependency resolution of the pyinstall command
"""
import os

from subprocess import CalledProcessError

import pytest

from pkglib_testing.util import (PkgTemplate, TmpVirtualEnv,
                                 create_package_from_template as pkg_t)

from pkglib_testing.pytest.simple_http_server import simple_http_test_server


HERE = os.getcwd()
USE_EGG_CACHE_VALUES = [True, False]


def _dist_inhouse_eggs(pkg, pypi, use_egg_cache):
    if use_egg_cache:
        pkg.env["VIRTUALENV_SEARCH_PATH"] = pypi.file_dir

    for p in [os.path.join(str(pkg.workspace), p)
              for p in os.listdir(pkg.workspace) if p.startswith("acme")]:
        pkg.run(" ".join(["python", os.path.join(p, "trunk", "setup.py"),
                          "bdist_egg", "--dist-dir=%s" % pypi.file_dir]))


def _get_pyinstall_cmd(env, arg, use_abs_python=True):
    prefix = (env.python + " ") if use_abs_python else ""
    return "%s%s/bin/pyinstall -v %s" % (prefix, env.virtualenv, arg)


def _exec_pyinstall(env, arg, *args, **kwargs):
    return env.run(_get_pyinstall_cmd(env, arg), *args, **kwargs)


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_setuptools(pytestconfig, simple_http_test_server, use_egg_cache):
    """ Creates template, runs pyinstall from the setuptools command
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg_t(pkg, "acme.bar-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        cmd = "%s %s/setup.py pyinstall -i %s acme.bar" % (pkg.python, pkg.trunk_dir, simple_http_test_server.uri)
        pkg.run(cmd, cd=HERE)

        cmd = '%s -c "import acme.bar"' % pkg.python
        pkg.run(cmd, capture=False, cd=HERE)

        installed = pkg.installed_packages()
        assert installed['acme.bar'].isrel


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_cmdline(pytestconfig, simple_http_test_server, use_egg_cache):
    """ As above but running pyinstall from the command-line
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg_t(pkg, "acme.bar-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        assert "acme.bar" not in pkg.installed_packages()

        _exec_pyinstall(pkg, "-i %s acme.bar" % simple_http_test_server.uri, cd=HERE)

        pkg.run('%s -c "import acme.bar"' % pkg.python, capture=False, cd=HERE)
        assert pkg.installed_packages()['acme.bar'].isrel


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_fails_on_nonexistent_package(pytestconfig, simple_http_test_server, use_egg_cache):

    with TmpVirtualEnv() as pkg:
        assert "acme.fubar" not in pkg.installed_packages()

        with pytest.raises(Exception):
            _exec_pyinstall(pkg, "-i %s acme.fubar" % simple_http_test_server.uri)

        assert "acme.fubar" not in pkg.installed_packages()


def test_pyinstall_fails_on_nonexistent_package_no_pypi(pytestconfig):

    with TmpVirtualEnv() as pkg:
        assert "acme.fubar" not in pkg.installed_packages()

        with pytest.raises(Exception):
            _exec_pyinstall(pkg, "acme.fubar")

        assert "acme.fubar" not in pkg.installed_packages()


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_fails_on_incompatible_pinned_dependencies(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA

    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c==1.0') as pkg:
        pkg.dead = True  # delete on exit

        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c==1.1')
        pkg_t(pkg, "acme.c-1.0")
        pkg_t(pkg, "acme.c-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        with pytest.raises(Exception):
            _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)

        assert 'acme.b' not in pkg.installed_packages()
        # nothing happened
        assert pkg.installed_packages()["acme.c"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_full_dependency_walkback_in_version_conflict_exception(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c==1.0') as pkg:
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c==1.1')
        pkg_t(pkg, "acme.c-1.0")
        pkg_t(pkg, "acme.c-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        with pytest.raises(Exception) as exc:
            _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri, capture=True)

        assert """There is a version conflict.
We already have: acme.c 1.0
required by acme.c==1.0 (acme.c 1.0)
  required by acme.a (acme.a 1.0)
which is incompatible with acme.c==1.1
  required by acme.b (acme.b 1.0)
""" in exc.value.output


@pytest.mark.xfail(reason="force option not supported yet")
@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_force_ignores_incompatible_pinned_dependencies(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c==1.0') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c==1.1')
        pkg_t(pkg, "acme.c-1.0")
        pkg_t(pkg, "acme.c-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        _exec_pyinstall(pkg, "-i %s --force acme.b" % simple_http_test_server.uri)
        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.c"].version == "1.1"
        assert 'acme.a' in pkg.installed_packages()  # but acme.a is now broken


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_respects_existing_pins(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c==1.0') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c')
        pkg_t(pkg, "acme.c-1.0")
        pkg_t(pkg, "acme.c-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.c"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_upgrades_where_required_by_pins(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.c-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c==1.1')
        pkg_t(pkg, "acme.c-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)

        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.c"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_downgrades_as_required_by_pins(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.c-1.0")
        pkg_t(pkg, "acme.c-1.1")
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c==1.0')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.1"

        out = _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri, capture=True)
        assert 'Downgrading acme.c from 1.1 to 1.0' in out
        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.c"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_opportunistically_upgrades_dependent_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.c-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        pkg_t(pkg, "acme.c-1.1")
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.c')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.c"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_opportunistically_upgrades_installed_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0') as pkg:
        pkg.dead = True  # delete on exit
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.0"

        pkg_t(pkg, "acme.a-1.1")
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.a')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert 'acme.b' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.a"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_upgrades_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0') as pkg:
        pkg.dead = True  # delete on exit
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.0"

        pkg_t(pkg, "acme.a-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_upgrades_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0') as pkg:
        pkg.dead = True  # delete on exit
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.0"

        pkg_t(pkg, "acme.a-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-U -i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_upgrade_upgrades_dependent_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.1', install_requires='acme.c==1.1') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.a-1.0", install_requires='acme.c==1.0')
        pkg_t(pkg, "acme.c-1.1")
        pkg_t(pkg, "acme.c-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a==1.0" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.0"
        assert pkg.installed_packages()["acme.c"].version == "1.0"

        _exec_pyinstall(pkg, "-i %s acme.a==1.1" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.1"
        assert pkg.installed_packages()["acme.c"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_downgrade_downgrades_dependent_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.1', install_requires='acme.c==1.1') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.a-1.0", install_requires='acme.c==1.0')
        pkg_t(pkg, "acme.c-1.1")
        pkg_t(pkg, "acme.c-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.1"
        assert pkg.installed_packages()["acme.c"].version == "1.1"

        _exec_pyinstall(pkg, "-i %s acme.a==1.0" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.0"
        assert pkg.installed_packages()["acme.c"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_installs_required_dependencies_when_backtracking(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.c\nacme.b') as pkg:
        pkg.dead = True  # delete on exit
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.d')
        pkg_t(pkg, "acme.b-1.1", install_requires='acme.d')
        pkg_t(pkg, "acme.c-1.0", install_requires='acme.b==1.0')
        pkg_t(pkg, "acme.d-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        assert 'acme.a' in pkg.installed_packages()
        assert pkg.installed_packages()["acme.b"].version == "1.0"
        assert pkg.installed_packages()["acme.c"].version == "1.0"
        assert pkg.installed_packages()["acme.d"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_backtrack_requirement_merged_to_prev(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.x>=1.0') as pkg:
        pkg_t(pkg, "acme.x-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, 'acme.x-1.1')
        pkg_t(pkg, 'acme.y-1.0', install_requires='acme.x==1.0')
        pkg_t(pkg, 'acme.b-1.0', install_requires='acme.y\nacme.x')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert pkg.installed_packages()['acme.x'].version == '1.0'


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_backtrack_requirement_merged_to_current(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.x') as pkg:
        pkg_t(pkg, "acme.x-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, 'acme.x-1.1')
        pkg_t(pkg, 'acme.y-1.0', install_requires='acme.x==1.0')
        pkg_t(pkg, 'acme.b-1.0', install_requires='acme.y\nacme.x>=1.0')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert pkg.installed_packages()['acme.x'].version == '1.0'


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_backtrack_requirement_merged_to_new(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.x>=1.0') as pkg:
        pkg_t(pkg, "acme.x-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, 'acme.x-1.1')
        pkg_t(pkg, 'acme.y-1.0', install_requires='acme.x==1.0')
        pkg_t(pkg, 'acme.b-1.0', install_requires='acme.y\nacme.x<=1.1')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        assert pkg.installed_packages()['acme.x'].version == '1.0'


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_dev_skips_pinned_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.b==1.1') as pkg:
        pkg_t(pkg, "acme.b-1.1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, "acme.b-1.2.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        with pytest.raises(CalledProcessError) as exc:
            _exec_pyinstall(pkg, "-i %s -U --dev acme.b" % simple_http_test_server.uri, capture=True)

        assert ('Unable to update package acme.b, it is pinned (See list above)'
                in exc.value.output)
        assert pkg.installed_packages()["acme.b"].version == "1.1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_dev_updates_to_dev(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.1') as pkg:
        pkg_t(pkg, "acme.a-1.2.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()["acme.a"].version == "1.1"

        _exec_pyinstall(pkg, "-i %s --dev acme.a" % simple_http_test_server.uri)

        assert pkg.installed_packages()["acme.a"].version == "1.2.dev1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_dev_updates_packages_with_minimum_version_requirements(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.b>=1.0') as pkg:
        pkg_t(pkg, "acme.b-1.1.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, "acme.b-1.2.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s -U --dev acme.b" % simple_http_test_server.uri)

        assert pkg.installed_packages()["acme.b"].version == "1.2.dev1"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_dev_respects_existing_pins(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.b-1.0.dev1', install_requires='acme.a') as pkg:
        pkg_t(pkg, "acme.c-1.0", install_requires='acme.a==1.0')
        pkg_t(pkg, "acme.a-1.0")
        pkg_t(pkg, "acme.a-1.1.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.b" % simple_http_test_server.uri)
        _exec_pyinstall(pkg, "-i %s acme.c" % simple_http_test_server.uri)

        pkg_t(pkg, "acme.b-1.1", install_requires='acme.a')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s -U --dev acme.b" % simple_http_test_server.uri)

        assert pkg.installed_packages()["acme.a"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_pyinstall_update_dev_relocated_pin(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    """
         A                A
       / | \            / | \
    ==1.0|==1.0        /  |  \
     B ==1.0 C    =>  B   |   C
      \  |  /          \  |  /
       \ | /         ==1.0| /
         D                D
    """
    with PkgTemplate('acme.a-1.0', install_requires=('acme.b==1.0', 'acme.d==1.0',
                                                    'acme.c==1.0')) as pkg:
        pkg_t(pkg, "acme.b-1.0", install_requires='acme.d')
        pkg_t(pkg, "acme.c-1.0", install_requires='acme.d')
        pkg_t(pkg, "acme.d-1.0")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        pkg_t(pkg, 'acme.a-1.1.dev1', install_requires='acme.b\nacme.d\nacme.c')
        pkg_t(pkg, "acme.b-1.1.dev1", install_requires='acme.d==1.0')
        pkg_t(pkg, "acme.c-1.1.dev1", install_requires='acme.d')
        pkg_t(pkg, "acme.d-1.1.dev1")
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s --dev acme.a" % simple_http_test_server.uri)
        assert pkg.installed_packages()['acme.d'].version == '1.0'


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_develop_pulls_in_deps_of_other_deps_in_development_1(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    """
    1) given the following package hierarchy:

               A
              /
            B (fetched without dependencies)
            |
            C
            |
            D

    2) and provided that package B has been set-up using:
         $ python setup.py develop --no-deps --no-build

    3) executing the following command for pacakge D:
         $ python setup.py develop

    4) should pull in package A

    """
    with PkgTemplate(name='acme.a-1.0') as pkg:
        _, acmeb_trunk = pkg_t(pkg, "acme.b-1.0", install_requires='acme.a==1.0')
        pkg_t(pkg, "acme.c-1.0", install_requires='acme.b==1.0')
        _, acmed_trunk = pkg_t(pkg, "acme.d-1.0", install_requires='acme.c==1.0',
                              metadata=dict(tests_require=''))
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        pkg.run("%s setup.py develop --no-deps --no-build -i %s" %
                (pkg.python, simple_http_test_server.uri), cd=acmeb_trunk)
        assert "acme.a" not in pkg.installed_packages()

        pkg.run("%s setup.py develop -i %s" % (pkg.python, simple_http_test_server.uri),
                cd=acmed_trunk)
        assert pkg.installed_packages()["acme.a"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_develop_pulls_in_deps_of_other_deps_in_development_2(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    """
    1) given the following package hierarchy:

                                         A
                                       /   \
                                    ==1.0  (any)
                                     |     /
      (fetched without dependencies) B   /
                                     | /
                                     C (needs any version of A)
                                     |
                                     D

    2) and provided that package B has been set-up using:
         $ python setup.py develop --no-deps --no-build

    3) executing the following command for pacakge D:
         $ python setup.py develop

    4) should pull in package A version 1.0

    """
    with PkgTemplate(name='acme.a-1.0') as pkg:
        pkg_t(pkg, "acme.a-2.0")
        _, acmeb_trunk = pkg_t(pkg, "acme.b-1.0", install_requires='acme.a==1.0')
        pkg_t(pkg, "acme.c-1.0", install_requires='acme.a\nacme.b==1.0')
        _, acmed_trunk = pkg_t(pkg, "acme.d-1.0", install_requires='acme.c==1.0',
                              metadata=dict(tests_require=''))
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        pkg.run("%s setup.py develop --no-deps --no-build -i %s" % (pkg.python, simple_http_test_server.uri),
                cd=acmeb_trunk)
        assert "acme.a" not in pkg.installed_packages()

        pkg.run("%s setup.py develop -i %s" % (pkg.python, simple_http_test_server.uri), cd=acmed_trunk)
        assert pkg.installed_packages()["acme.a"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_develop_considers_existing_version_requirements_on_uninstalled_packages(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    """
        A (1.0, 2.0 available)
       / \
    ==1.0 \
     /     \
    B       C

    1. Develop B with --no-deps (or develop B then uninstall A)
    2. Develop C; A==1.0 should be installed, not A==2.0
    """
    with PkgTemplate(name='acme.a-1.0') as pkg:
        pkg.install_package("pytest-cov")
        pkg_t(pkg, "acme.a-2.0")
        _, b = pkg_t(pkg, "acme.b-1.0", install_requires='acme.a==1.0')
        _, c = pkg_t(pkg, "acme.c-1.0", install_requires='acme.a')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        pkg.run("%s setup.py develop --no-deps --no-build -i %s" % (pkg.python, simple_http_test_server.uri), cd=b)
        assert "acme.a" not in pkg.installed_packages()

        pkg.run("%s setup.py develop -i %s" % (pkg.python, simple_http_test_server.uri), cd=c)
        assert pkg.installed_packages()["acme.a"].version == "1.0"


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_downgrade_from_dev_to_final_handles_multi_level_dependencies(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.b==1.0') as pkg:
        pkg_t(pkg, "acme.a-1.1.dev1", install_requires='acme.b==1.1')
        pkg_t(pkg, 'acme.b-1.0', install_requires='acme.c==1.0')
        pkg_t(pkg, 'acme.b-1.1', install_requires='acme.c==1.1')
        pkg_t(pkg, 'acme.c-1.0')
        pkg_t(pkg, 'acme.c-1.1')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s --dev acme.a" % simple_http_test_server.uri)

        assert pkg.installed_packages()['acme.a'].version == '1.1.dev1'
        assert pkg.installed_packages()['acme.b'].version == '1.1'
        assert pkg.installed_packages()['acme.c'].version == '1.1'

        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)
        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        assert pkg.installed_packages()['acme.a'].version == '1.0'
        assert pkg.installed_packages()['acme.b'].version == '1.0'
        assert pkg.installed_packages()['acme.c'].version == '1.0'


@pytest.mark.parametrize('use_egg_cache', USE_EGG_CACHE_VALUES)
def test_upgrade_handles_multi_level_dependencies(pytestconfig, simple_http_test_server, use_egg_cache):  # @UnusedVariable # NOQA
    with PkgTemplate(name='acme.a-1.0', install_requires='acme.b==1.0') as pkg:
        pkg_t(pkg, 'acme.b-1.0', install_requires='acme.c==1.0')
        pkg_t(pkg, 'acme.c-1.0')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        assert pkg.installed_packages()['acme.a'].version == '1.0'
        assert pkg.installed_packages()['acme.b'].version == '1.0'
        assert pkg.installed_packages()['acme.c'].version == '1.0'

        pkg_t(pkg, "acme.a-1.1", install_requires='acme.b==1.1')
        pkg_t(pkg, 'acme.b-1.1', install_requires='acme.c==1.1')
        pkg_t(pkg, 'acme.c-1.1')
        _dist_inhouse_eggs(pkg, simple_http_test_server, use_egg_cache)

        _exec_pyinstall(pkg, "-i %s acme.a" % simple_http_test_server.uri)

        assert pkg.installed_packages()['acme.a'].version == '1.1'
        assert pkg.installed_packages()['acme.b'].version == '1.1'
        assert pkg.installed_packages()['acme.c'].version == '1.1'
