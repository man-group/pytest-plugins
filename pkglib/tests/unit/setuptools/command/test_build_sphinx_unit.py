""" Sphinx Documentation Builder
"""
import imp
import os
import re
import sys

import pytest

from mock import Mock, patch, ANY, call, sentinel
from setuptools import Distribution

import pkglib  # @UnusedImport

from pkglib.six.moves import ExitStack

from pkglib.setuptools.command import build_sphinx

from .runner import _mock_modules

_cmd = build_sphinx.__name__


def test_initialize_options__uses_reasonable_defaults():
    t = build_sphinx.build_sphinx(Distribution())
    assert t.build_dir == 'build/sphinx'
    assert t.source_dir == 'docs'


@pytest.mark.parametrize("no_doctest", (False, True))
def test_finilize_options__negates_doc_test_options(no_doctest):
    t = build_sphinx.build_sphinx(Distribution())
    t.no_doctest = no_doctest
    t.finalize_options()
    assert t.doctest == (not no_doctest)


def _test_obj_in_package(pkg_name, obj):
    t = build_sphinx.build_sphinx(Distribution(attrs={"name": pkg_name}))
    return t._obj_in_package(obj)


def test_obj_in_package__accepts_module_type_from_the_same_package():
    assert _test_obj_in_package("Test", imp.new_module("Test.subpkg"))


def test_obj_in_package__rejects_module_type_from_another_package():
    assert not _test_obj_in_package("Test", imp.new_module("Other.subpkg"))


def test_obj_in_package__accepts_module_object_from_the_same_package():
    assert _test_obj_in_package("Test", Mock(__module__="Test.subpkg"))


def test_obj_in_package__rejects_module_object_from_another_package():
    assert not _test_obj_in_package("Test", Mock(__module__="Other.subpkg"))


def test_skip_member__accepts_obj_from_the_same_package():
    t = build_sphinx.build_sphinx(Distribution())
    with patch.object(t, "_obj_in_package", return_value=True):
        assert not t._skip_member("foo")


def test_skip_member__rejects_obj_from_another_package():
    t = build_sphinx.build_sphinx(Distribution())
    with patch.object(t, "_obj_in_package", return_value=False):
        assert t._skip_member("foo")


def test_skip_member__skips_obj_having_name_starting_with_underscore():
    t = build_sphinx.build_sphinx(Distribution())
    with patch.object(t, "_obj_in_package", return_value=True):
        assert t._skip_member(Mock(__name__="_foo"))


def test_process_docstring__accepts_doctests_the_same_package():
    t = build_sphinx.build_sphinx(Distribution())
    lines = [">>> print('hello')"]
    expected_lines = lines[:]

    with patch.object(t, "_obj_in_package", return_value=True):
        t._process_docstring("foo", lines)

    assert expected_lines


def _test_process_docstring(lines, obj_in_package):
    t = build_sphinx.build_sphinx(Distribution())
    originals = lines[:]

    with patch.object(t, "_obj_in_package", return_value=obj_in_package):
        t._process_docstring("foo", lines)

    return originals


def test_process_docstring__skips_doctests_from_another_package():
    lines = [">>> assert True == True", "   >>> import sys"]
    originals = _test_process_docstring(lines, False)

    assert len(lines) == len(originals)
    for i in range(len(lines)):
        m = re.match("^%s *# *doctest: *\+SKIP *$" % originals[i], lines[i])
        assert m


def test_process_docstring__only_affects_doctests_from_another_package():
    lines = ["some documentation string"]
    originals = _test_process_docstring(lines, False)

    assert lines == originals


def test_make_sphinx_setup__autodoc_external_methods_is_set():
    t = build_sphinx.build_sphinx(Distribution())
    t.autodoc_external_methods = True
    t._process_docstring = Mock()
    prev_setup = Mock()
    app = Mock()

    setup = t._make_sphinx_setup(prev_setup)

    setup(app)

    prev_setup.assert_called_once_with(app)
    app.connect.assert_called_once_with("autodoc-process-docstring", ANY)
    app.connect.call_args[0][1]("app", "what", "name", "obj", "opts", "lines")

    t._process_docstring.assert_called_once_with("obj", "lines")


def test_make_sphinx_setup__autodoc_external_methods_is_not_set():
    t = build_sphinx.build_sphinx(Distribution())
    t.autodoc_external_methods = False
    t._skip_member = Mock()
    prev_setup = Mock()
    app = Mock()

    setup = t._make_sphinx_setup(prev_setup)

    setup(app)

    prev_setup.assert_called_once_with(app)
    app.connect.assert_called_once_with("autodoc-skip-member", ANY)
    app.connect.call_args[0][1]("app", "what", "name", "obj", "opts", "lines")

    t._skip_member.assert_called_once_with("obj")


def test_run_sphinx():
    t = build_sphinx.build_sphinx(Distribution(attrs={"name": "RunSphinx",
                                                      "version": sentinel.v}))
    t._make_sphinx_setup = Mock()
    t.all_files = sentinel.all_files
    builder_name = "my_builder"

    sphinx_mock = {"Sphinx": Mock()}
    makedirs_mock = Mock()

    expected_build_dir = os.path.join(t.build_dir, builder_name)
    expected_doc_dir = os.path.join(t.build_dir, "doctrees")

    with ExitStack() as stack:
        stack.enter_context(_mock_modules({"sphinx.application": sphinx_mock}))
        stack.enter_context(patch("os.path.isdir", return_value=False))
        stack.enter_context(patch("os.makedirs", new=makedirs_mock))
        stack.enter_context(patch("os.path.abspath",
                                  new=lambda f: "ABS: " + f))
        t.run_sphinx(builder_name)

    # Check directories were created
    calls = [call(t.build_dir),
             call(expected_doc_dir),
             call(expected_build_dir)]
    makedirs_mock.assert_has_calls(calls, any_order=True)

    sphinx = sphinx_mock["Sphinx"]
    sphinx.assert_called_once_with(srcdir="ABS: " + t.source_dir,
                                   confdir="ABS: " + t.source_dir,
                                   outdir="ABS: " + expected_build_dir,
                                   doctreedir="ABS: " + expected_doc_dir,
                                   buildername=builder_name,
                                   confoverrides={"version": sentinel.v,
                                                  "release": sentinel.v},
                                   status=sys.stdout,
                                   freshenv=False)


def _test_run(mocks, attrs={}, run_sphinx_rc=0):
    dist_attrs = {"name": "RunSphinx", "version": sentinel.v}
    t = build_sphinx.build_sphinx(Distribution(attrs=dist_attrs))
    for k, v in attrs.items():
        setattr(t, k, v)
    t.run_sphinx = Mock(return_value=run_sphinx_rc)

    with ExitStack() as stack:
        fbg = stack.enter_context(patch(_cmd + ".fetch_build_eggs"))
        d_autodoc = stack.enter_context(patch(_cmd + ".dynamicautodoc"))
        autodoc = stack.enter_context(patch(_cmd + ".autodoc"))
        mocks["dynamicautodoc"] = d_autodoc
        mocks["autodoc"] = autodoc
        mocks["cmd"] = t
        try:
            t.run()
        except:
            # Need to re-raise here because of some weird `pytest.raises`
            # and `ExitStack` incompatibility bug surfacing on Python 2, which
            # causes the underlying exception to be returned instead of:
            # `py._code.code.ExceptionInfo`
            raise
        finally:
            assert fbg.called_once_with(["Sphinx", "numpydoc"])


def test_run__dynamic_autodoc():
    m = {}
    with pytest.raises(SystemExit) as ex:
        _test_run(m, {"autodoc_dynamic": True})

    assert ex.value.code == 0
    cmd = m["cmd"]
    dist = cmd.distribution
    assert call("html",) in cmd.run_sphinx.call_args_list
    m["dynamicautodoc"].generate.assert_called_once_with(dist)


def test_run__autodoc():
    m = {}
    with pytest.raises(SystemExit) as ex:
        _test_run(m, {"autodoc_dynamic": False})

    assert ex.value.code == 0
    cmd = m["cmd"]
    dist = cmd.distribution
    assert call("html",) in cmd.run_sphinx.call_args_list
    m["autodoc"].generate.assert_called_once_with(dist)


def test_run__runs_doctest():
    m = {}
    with pytest.raises(SystemExit) as ex:
        _test_run(m, {"doctest": True})

    assert ex.value.code == 0
    assert call("doctest",) in m["cmd"].run_sphinx.call_args_list


def test_run__skips_doctest():
    m = {}
    _test_run(m, {"doctest": False})
    assert call("doctest",) not in m["cmd"].run_sphinx.call_args_list


def test_run__skips_doc_generation_if_when_no_build_is_used():
    m = {}
    _test_run(m, {"no_build": True, "doctest": False})
    assert not m["cmd"].run_sphinx.called


def test_run__run_sphinx_returns_non_zero_rc__exits_without_doctest():
    m = {}
    with pytest.raises(SystemExit) as ex:
        _test_run(m, {"no_build": False, "doctest": True}, run_sphinx_rc=1)
    assert ex.value.code == 1
    assert m["cmd"].run_sphinx.called
    assert not call("doctest",) in m["cmd"].run_sphinx.call_args_list
