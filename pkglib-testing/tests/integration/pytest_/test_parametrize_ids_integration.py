from pkg_resources import resource_filename  # @UnresolvedImport
from pkglib_testing.fixtures.package import PkgTemplate
from distutils.dir_util import copy_tree


def test_parametrize_ids_generates_ids(pytestconfig):
    test_dir = resource_filename('pkglib_testing', '../../tests/integration/pytest/parametrize_ids')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        pkg.install_package('pkglib_testing')
        copy_tree(test_dir, pkg.trunk_dir)
        output = pkg.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_parametrized.py'],
                                       pytestconfig, cd=pkg.trunk_dir)
    expected = '''
<Module 'tests/unit/test_parametrized.py'>
  <Function 'test_foo[sum-list]'>
  <Function 'test_foo[len-int]'>
'''
    assert expected in output


def test_parametrize_ids_leaves_nonparametrized(pytestconfig):
    test_dir = resource_filename('pkglib_testing', '../../tests/integration/pytest/parametrize_ids')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        pkg.install_package('pkglib_testing')
        copy_tree(test_dir, pkg.trunk_dir)
        output = pkg.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_non_parametrized.py'],
                                       pytestconfig, cd=pkg.trunk_dir)
    expected = '''
<Module 'tests/unit/test_non_parametrized.py'>
  <Function 'test_bar'>
'''
    assert expected in output


def test_handles_apparent_duplicates(pytestconfig):
    test_dir = resource_filename('pkglib_testing', '../../tests/integration/pytest/parametrize_ids')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        pkg.install_package('pkglib_testing')
        copy_tree(test_dir, pkg.trunk_dir)
        output = pkg.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_duplicates.py'],
                                       pytestconfig, cd=pkg.trunk_dir)
    expected = '''
<Module 'tests/unit/test_duplicates.py'>
  <Function 'test_foo[0-[1]]'>
  <Function 'test_foo[0-[1]#1]'>
  <Function 'test_foo[0-[1]#2]'>
'''
    assert expected in output


def test_truncates_long_ids(pytestconfig):
    test_dir = resource_filename('pkglib_testing', '../../tests/integration/pytest/parametrize_ids')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        pkg.install_package('pkglib_testing')
        copy_tree(test_dir, pkg.trunk_dir)
        output = pkg.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_long_ids.py'],
                                       pytestconfig, cd=pkg.trunk_dir)
    expected = '''
<Module 'tests/unit/test_long_ids.py'>
  <Function 'test_foo[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9...-None]'>
'''
    assert expected in output
