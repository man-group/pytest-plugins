from pkg_resources import resource_filename  # @UnresolvedImport
from pkglib.testing.util import PkgTemplate
from distutils.dir_util import copy_tree


def test_parametrize_ids_generates_ids(pytestconfig):
    test_dir = resource_filename('pkglib.testing', '../../tests/integration/pytest/parametrize_ids')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        pkg.install_package('pkglib.testing')
        copy_tree(test_dir, pkg.trunk_dir)
        output = pkg.run_with_coverage(['-m', 'pytest', '--collectonly', 'tests/unit/test_example.py'],
                                       pytestconfig, cd=pkg.trunk_dir)
    expected = '''
<Module 'tests/unit/test_example.py'>
  <Function 'test_foo[sum-list]'>
  <Function 'test_foo[len-int]'>
  <Function 'test_bar'>
'''
    assert expected in output
