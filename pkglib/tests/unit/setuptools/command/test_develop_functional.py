"""
Tests covering the 'develop' command
"""

from pkglib.setuptools.command.develop import develop

from .runner import (assert_dists_installed, assert_dists_in_pth,
                     create_dist, run_setuptools_cmd)


def _run_develop_cmd(dist_to_be_developed, virtualenv_dists=[],
                     available_dists=[], args=None):
    mocks = {}
    run_setuptools_cmd(develop,
                       dist=dist_to_be_developed,
                       virtualenv_dists=virtualenv_dists,
                       available_dists=available_dists,
                       mocks=mocks,
                       args=args)

    return mocks


def test_run__installs_setup_requirements():
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "1.0", setup_requires={"acme.a": "1.0"})

    m = _run_develop_cmd(prj_B, virtualenv_dists=[],
                         available_dists=[prj_A, prj_B])

    assert_dists_installed(m, prj_A, prj_B)
    assert_dists_in_pth(m, prj_B)


def test_run__skip_setup_requirements_which_are_already_installed():
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "1.0", setup_requires={"acme.a": "1.0"})

    m = _run_develop_cmd(prj_B, virtualenv_dists=[prj_A],
                         available_dists=[prj_A, prj_B])

    assert_dists_installed(m, prj_B)
    assert_dists_in_pth(m, prj_A, prj_B)


def test_run__re_adds_setup_requirements_if_also_in_install_requires():
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "1.0", requires={"acme.a": "1.0"})

    prj_C = create_dist("acme.c", "1.0",
                        setup_requires={"acme.a": "1.0"},
                        requires={"acme.b": "1.0"})

    m = _run_develop_cmd(prj_C, virtualenv_dists=[prj_A],
                         available_dists=[prj_A, prj_B, prj_C])

    assert_dists_installed(m, prj_B, prj_C)
    assert_dists_in_pth(m, prj_A, prj_B, prj_C)


def test_run__handles_cyclic_dependencies_of_setup_requires():
    prj_A = create_dist("acme.a", "1.0", requires={"acme.b": "1.0"})
    prj_B = create_dist("acme.b", "1.0", setup_requires={"acme.a": "1.0"})

    m = _run_develop_cmd(prj_B, virtualenv_dists=[prj_A],
                         available_dists=[prj_B])

    assert_dists_installed(m, prj_B)
    assert_dists_in_pth(m, prj_A, prj_B)


def test_run__pulls_in_deps_of_other_deps_in_development_1():
    """
    1) assume the following package hierarchy:

               A
              /
            B  (set-up without dependencies)
            |
            C
            |
            D

    2) provided that package B has been set-up using:
         $ python setup.py develop --no-deps --no-build

    3) the following should not fail for package D:
         $ python setup.py develop

    """
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "1.0", requires={"acme.a": "1.0"})
    prj_C = create_dist("acme.c", "1.0", requires={"acme.b": "1.0"})
    prj_D = create_dist("acme.d", "1.0", requires={"acme.c": "1.0"})

    m = _run_develop_cmd(prj_D, virtualenv_dists=[prj_B],
                         available_dists=[prj_A, prj_B, prj_C, prj_D])

    assert_dists_installed(m, prj_A, prj_C, prj_D)
    assert_dists_in_pth(m, prj_A, prj_B, prj_C, prj_D)


def test_run__pulls_in_deps_of_other_deps_in_development_2():
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

    prj_A10 = create_dist("acme.a", "1.0")
    prj_A20 = create_dist("acme.a", "2.0")

    prj_B = create_dist("acme.b", "1.0", requires={"acme.a": "1.0"})

    prj_C = create_dist("acme.c", "1.0", requires={"acme.b": "1.0",
                                                  "acme.a": None})

    prj_D = create_dist("acme.d", "1.0", requires={"acme.c": "1.0"})

    m = _run_develop_cmd(prj_D, virtualenv_dists=[prj_B],
                         available_dists=[prj_A10, prj_A20, prj_B, prj_C,
                                          prj_D])

    assert_dists_installed(m, prj_A10, prj_C, prj_D)
    assert_dists_in_pth(m, prj_A10, prj_B, prj_C, prj_D)


def test_run__installs_all_extras():
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "2.0")
    prj_C = create_dist("acme.c", "3.0")

    prj_D = create_dist("acme.d", "1.0",
                        extras_require={"bar": ["acme.a"],
                                        "foo": ["acme.b<=2.0",
                                                "acme.c>2.0"]})

    m = _run_develop_cmd(prj_D, available_dists=[prj_A, prj_B, prj_C, prj_D])

    assert_dists_installed(m, prj_A, prj_B, prj_C, prj_D)


def test_run__installs_all_test_dependencies():
    prj_A = create_dist("acme.a", "1.0")
    prj_B = create_dist("acme.b", "2.0", tests_require=["acme.a"])

    m = _run_develop_cmd(prj_B, available_dists=[prj_A, prj_B])

    assert_dists_installed(m, prj_A, prj_B)
    assert_dists_in_pth(m, prj_A, prj_B)


def test_run__skips_extras_if_no_extras_is_used():
    prj_A = create_dist("acme.a", "1.0", extras_require={"bar": "acme.b"})

    m = _run_develop_cmd(prj_A, available_dists=[prj_A], args=["--no-extras"])

    assert_dists_installed(m, prj_A)
    assert_dists_in_pth(m, prj_A)


def test_run__skips_test_dependencies_if_no_test_is_used():
    prj_A = create_dist("acme.a", "1.0", tests_require=["acme.b"])

    m = _run_develop_cmd(prj_A, available_dists=[prj_A], args=["--no-test"])

    assert_dists_installed(m, prj_A)
    assert_dists_in_pth(m, prj_A)


def test_run__skips_dependencies_if_no_deps_is_used():
    prj_A = create_dist("acme.a", "1.0",
                        extras_require={"bar": "acme.b"},
                        tests_require=["acme.c"])

    m = _run_develop_cmd(prj_A, available_dists=[prj_A], args=["--no-deps"])

    assert_dists_installed(m, prj_A)
    assert_dists_in_pth(m, prj_A)
