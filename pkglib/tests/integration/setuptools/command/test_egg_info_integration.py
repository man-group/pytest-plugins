from __future__ import print_function
import copy
import os

import pytest

from pkglib_testing.util import PkgTemplate
from pkglib_testing.pytest.util import svn_repo, workspace  # @UnusedImport # NOQA
from pkglib_testing.pytest.pypi import pypi_chishop  # @UnusedImport # NOQA
from pkglib.manage import read_allrevisions
from pkglib.patches.six_moves import ExitStack    # @UnresolvedImport

from pkglib_testing.pypi import create_pkg

from pkglib.pyenv import PythonInstallation

HERE = os.getcwd()


def _svn_info_revision(pkg, workspace, package_name):
    rev_info = pkg.run("svn info %s/%s" % (workspace, package_name),
                       capture=True)
    revno = []
    for line in rev_info.split('\n'):
        if line.startswith('Revision:'):
            revno.append(line.split()[1])
            break
    assert revno

    return revno[0]


def test_egg_info(svn_repo, workspace, pytestconfig):
    """ Creates template, runs setup.py egg_info
    """
    with PkgTemplate(name='acme.foo', repo_base=svn_repo.uri) as pkg:
        pkg.install_package('pytest-cov')
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            ("svn import %s/%s %s -m 'initial import'" %
             (pkg.workspace, 'acme.foo', pkg.vcs_uri)),
            'svn co %s/trunk %s/acme.foo' % (pkg.vcs_uri, workspace.workspace),
        ]]
        print(pkg.run_with_coverage(['%s/acme.foo/setup.py' %
                                     workspace.workspace, 'egg_info'],
                                    pytestconfig, cd=HERE))
        egg_dir = os.path.join(workspace.workspace, 'acme.foo',
                               'acme.foo.egg-info')
        egg_file = os.path.join(egg_dir, 'PKG-INFO')
        with open(egg_file) as fp:
            found = []
            for line in fp:
                if line.startswith('Home-page'):
                    assert line.split(':', 1)[1].strip() == pkg.vcs_uri
                    found.append(True)
                    break
            assert found
        revno = _svn_info_revision(pkg, workspace.workspace, 'acme.foo')
        revno_file = os.path.join(egg_dir, 'revision.txt')
        assert os.path.isfile(egg_file)
        with open(revno_file) as fp:
            assert fp.readline().strip() == revno


@pytest.mark.chishop
def test_new_build(pypi_chishop, svn_repo, pytestconfig):
    """ Tests the new-build linking mechanisms, whereby dev builds get their
    version numbers generated on the fly after checking the pypi server for the
    latest version.
    """
    metadata = dict(
        install_requires='acme.newbuild1',
    )

    def setup_py(pkg, cmd):
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        print(pkg.run_with_coverage([pkg.trunk_dir / 'setup.py'] + cmd,
                                    pytestconfig, cd=HERE, env=new_env))

    with ExitStack() as stack:
        pkg1 = stack.enter_context(create_pkg(pypi_chishop, svn_repo,
                                              'acme.newbuild1', dev=False))
        pkg2 = stack.enter_context(create_pkg(pypi_chishop, svn_repo,
                                              'acme.newbuild2',
                                              metadata=metadata, dev=False))
        pkg1.install_package('pytest-cov')
        pkg2.install_package('pytest-cov')

        setup_py(pkg1, ['egg_info', '--new-build'])
        egg_dir = pkg1.trunk_dir / 'acme.newbuild1.egg-info'
        egg_file = egg_dir / 'PKG-INFO'
        assert 'Version: 0.0.dev1' in egg_file.lines(retain=False)

        # Now upload the dev package twice check we get a new build number
        # the next time round
        setup_py(pkg1, ['egg_info', '--new-build', 'bdist_egg', 'upload',
                        '--show-response'])
        setup_py(pkg1, ['egg_info', '--new-build', 'bdist_egg', 'upload',
                        '--show-response'])

        assert 'Version: 0.0.dev2' in egg_file.lines(retain=False)

        # Remove the other package and re-run develop for the second
        # package to get the new dev egg dependency
        setup_py(pkg2, ['uninstall', '-y', 'acme.newbuild1'])
        setup_py(pkg2, ['develop', '-i', '%s/simple' % pypi_chishop.uri])

        # Now make a new build and check the other package is a pinned
        # dependency at the new build number
        setup_py(pkg2, ['egg_info', '--new-build'])
        egg_dir = pkg2.trunk_dir / 'acme.newbuild2.egg-info'
        requires = egg_dir / 'requires.txt'
        assert requires.lines(retain=False) == ['acme.newbuild1==0.0.dev2']


@pytest.mark.chishop
def test_egg_revisions(pypi_chishop, svn_repo, workspace, pytestconfig):  # @UnusedVariable # NOQA
    #pypi_chishop.restore()
    package1_metadata = dict(version='1.2.3',)
    package2_metadata = dict(version='4.5.6',
                             install_requires='acme.er.package1==1.2.3')
    package3_metadata = dict(version='7.8.9',
                             install_requires='acme.er.package2==4.5.6')

    with ExitStack() as stack:
        pkg1 = stack.enter_context(create_pkg(pypi_chishop, svn_repo,
                                              'acme.er.package1',
                                              metadata=package1_metadata,
                                              dev=False))
        pkg2 = stack.enter_context(create_pkg(pypi_chishop, svn_repo,
                                              'acme.er.package2',
                                              metadata=package2_metadata,
                                              dev=False))
        pkg3 = stack.enter_context(PkgTemplate(name='acme.package3',
                                               repo_base=svn_repo.uri,
                                               metadata=package3_metadata))
        pkg3.run('%s %s/bin/easy_install -i %s/simple acme.er.package2'
                 % (pkg3.python, pkg3.virtualenv, pypi_chishop.uri))

        py_env = PythonInstallation(pkg3.python)
        egg = os.path.join(pkg3.virtualenv, 'lib',
                           'python' + py_env.short_version(2), 'site-packages',
                           'acme.er.package2-4.5.6-%s.egg' % py_env.py_version())
        name_to_revno = dict((name, str(revision))
                             for name, _, _, revision in read_allrevisions(egg))

        assert len(name_to_revno) == 2
        assert (name_to_revno['acme.er.package1'] ==
                _svn_info_revision(pkg3, pkg1.workspace, 'acme.er.package1'))
        assert (name_to_revno['acme.er.package2'] ==
                _svn_info_revision(pkg3, pkg2.workspace, 'acme.er.package2'))
