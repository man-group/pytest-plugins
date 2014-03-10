"""
Tests covering dependency resolution of the pyinstall command
"""
import os
import sys

import pytest

from mock import ANY, patch
from pkg_resources import Requirement

from pkglib.scripts.pyinstall import main as pyinstall_script
from pkglib.setuptools.command.pyinstall import pyinstall

from zc.buildout.easy_install import VersionConflict

from .runner import (assert_dists_installed, assert_dists_in_pth,
                     assert_scripts_written, create_dist,
                     _easy_install_mocks, _proc_dist_spy, run_setuptools,
                     _update_pth_spy)


__PYTHON_SCRIPT = "print('hello')"


def run_pyinstall_cmd(dist_to_be_installed, virtualenv_dists=[],
                      available_dists=[], mocks={}, dist_to_install=None):

    if not dist_to_install:
        dist_to_install = dist_to_be_installed.project_name

    def run_pyinstall_setuptools(**attrs):
        if 'cmdclass' in attrs:
            del attrs['cmdclass']
        with patch('pkglib.scripts.pyinstall.pyinstall',
                   new=attrs.pop("__command")):
            pyinstall_script(**attrs)

    run_setuptools(run_pyinstall_setuptools, pyinstall,
                   args=[dist_to_install, "-v"],
                   virtualenv_dists=virtualenv_dists,
                   available_dists=available_dists, mocks=mocks)


def test_run__fails_on_incompatible_pins():
    prj_A = create_dist("acme.a", "1.0", requires={"acme.c": "1.0"})
    prj_B = create_dist("acme.b", "1.0", requires={"acme.c": "1.1"})
    prj_C10 = create_dist("acme.c", "1.0")
    prj_C11 = create_dist("acme.c", "1.1")

    m = {}
    with pytest.raises(VersionConflict):
        run_pyinstall_cmd(prj_B,
                          virtualenv_dists=[prj_A, prj_C10],
                          available_dists=[prj_B, prj_C11],
                          mocks=m)

    get_dist_spy = m['pkglib.setuptools.buildout.Installer._get_dist']
    get_dist_spy.assert_called_once_with(Requirement.parse("acme.b"), ANY,
                                         False)
    assert not m[_easy_install_mocks][_proc_dist_spy].called
    assert not m[_easy_install_mocks][_update_pth_spy].called


def test_run__respects_existing_pins():
    prj_A = create_dist("acme.a", "1.0", requires={"acme.c": "1.0"})
    prj_B = create_dist("acme.b", "1.0", requires={"acme.c": None})
    prj_C10 = create_dist("acme.c", "1.0")
    prj_C11 = create_dist("acme.c", "1.1")

    m = {}
    run_pyinstall_cmd(prj_B,
                      virtualenv_dists=[prj_A, prj_C10],
                      available_dists=[prj_B, prj_C11],
                      mocks=m)

    assert_dists_installed(m, prj_B)
    assert_dists_in_pth(m, prj_A, prj_B, prj_C10)


def test_run__keeps_required_dependencies_when_backtracking():
    prj_A10 = create_dist("acme.a", "1.0", requires={"acme.b": "1.0",
                                                    "acme.c": "1.0",
                                                    "acme.d": "1.0"})

    prj_A20 = create_dist("acme.a", "2.0", requires={"acme.b": None,
                                                    "acme.d": None})

    prj_B_10 = create_dist("acme.b", "1.0", requires={"acme.a": "1.0"})
    prj_B_20 = create_dist("acme.b", "2.0", requires={"acme.c": "1.0"})

    prj_C = create_dist("acme.c", "1.0")
    projectd = create_dist("acme.d", "1.0", requires={"acme.a": "1.0"})

    m = {}
    run_pyinstall_cmd(prj_A10,
                      virtualenv_dists=[],
                      available_dists=[prj_A10, prj_A20, prj_B_10,
                                       prj_B_20, prj_C, projectd],
                      mocks=m)

    assert_dists_installed(m, prj_A10, prj_B_10, prj_C, projectd)
    assert_dists_in_pth(m, prj_A10, prj_B_10, prj_C, projectd)


def test_run__combines_requirements():
    prj_A = create_dist("acme.a", "1.0", requires={"acme.b": None,
                                                  "acme.c": ">=1.1"})

    prj_B = create_dist("acme.b", "1.0", requires={"acme.c": "<=1.1"})

    prj_C = [create_dist("acme.c", ver) for ver in ("1.0", "1.1", "1.2")]

    m = {}
    run_pyinstall_cmd(prj_A,
                      virtualenv_dists=[],
                      available_dists=[prj_A, prj_B] + prj_C,
                      mocks=m)

    assert_dists_installed(m, prj_A, prj_B, prj_C[1])
    assert_dists_in_pth(m, prj_A, prj_B, prj_C[1])


def test_run__upgrades_where_required_by_pins():
    prj_A = create_dist("acme.a", "1.0", requires={"acme.c": None})

    prj_B = create_dist("acme.b", "1.0", requires={'acme.c': "1.1"})

    prj_C10 = create_dist("acme.c", "1.0")
    prj_C11 = create_dist("acme.c", "1.1")

    m = {}
    run_pyinstall_cmd(prj_B,
                      virtualenv_dists=[prj_A, prj_C10],
                      available_dists=[prj_A, prj_B, prj_C10, prj_C11],
                      mocks=m)

    assert_dists_installed(m, prj_B, prj_C11)
    assert_dists_in_pth(m, prj_A, prj_B, prj_C11)


def test_run__correctly_installs_extras():
    prj_A10 = create_dist("acme.a", "1.0")
    prj_A20 = create_dist("acme.a", "2.0")

    prj_B = create_dist("acme.b", "1.0.dev1",
                        extras_require={"extra": "acme.a==1.0"})

    prj_C = create_dist("acme.c", "1.0.dev1", requires={"acme.b[extra]": None,
                                                       "acme.a": None})

    m = {}
    run_pyinstall_cmd(prj_C,
                      virtualenv_dists=[prj_B],
                      available_dists=[prj_A10, prj_A20, prj_B, prj_C],
                      mocks=m)

    assert_dists_installed(m, prj_C, prj_A10)
    assert_dists_in_pth(m, prj_A10, prj_B, prj_C)


def test_run__respects_pins_of_extras():
    prj_A10 = create_dist("acme.a", "1.0")
    prj_A20 = create_dist("acme.a", "2.0")

    prj_B = create_dist("acme.b", "1.0.dev1",
                        extras_require={"extra": "acme.a==1.0"})

    prj_C = create_dist("acme.c", "1.0.dev1", requires={"acme.b[extra]": None})

    prj_D = create_dist("acme.d", "1.0.dev1", requires={"acme.a": None})

    m = {}
    run_pyinstall_cmd(prj_D,
                      virtualenv_dists=[prj_A10, prj_B, prj_C],
                      available_dists=[prj_A10, prj_A20, prj_B, prj_C, prj_D],
                      mocks=m)

    assert_dists_installed(m, prj_D)
    assert_dists_in_pth(m, prj_A10, prj_B, prj_C, prj_D)


def test_run__installs_wrapped_python_script():
    script_name = "test_raw_python.py"
    original_content = "#!/usr/bin/env python\n" + __PYTHON_SCRIPT
    original_content = original_content.encode('utf-8')
    expect = ("#!%s\n"
              "# EASY-INSTALL-SCRIPT: 'acme.a==1.0','test_raw_python.py'\n"
              "__requires__ = 'acme.a==1.0'\n"
              "import pkg_resources\n"
              "pkg_resources.run_script('acme.a==1.0', 'test_raw_python.py')\n"
              % sys.executable)
    extra_egg_info = {os.path.join('scripts', script_name): original_content}
    prj_A = create_dist("acme.a", "1.0", extra_egg_info=extra_egg_info)

    m = {}
    run_pyinstall_cmd(prj_A, mocks=m, available_dists=[prj_A])

    assert_dists_installed(m, prj_A)
    assert_dists_in_pth(m, prj_A)
    assert_scripts_written(m, {script_name: expect})
