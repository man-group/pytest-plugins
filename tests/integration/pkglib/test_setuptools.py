"""
Tests covering all the setuptools extensions, except for
upload, register and upload_docs which are done in test_pypi_integration
"""
import sys
import os
import subprocess
import copy

import pytest
import path
from distutils.dir_util import copy_tree
import xml.etree.cElementTree as etree

from pkglib.testing.util import PkgTemplate
from pkglib.testing.pytest.util import pytest_funcarg__svn_repo, pytest_funcarg__workspace
from pkglib.testing.pytest.jenkins_server import pytest_funcarg__jenkins_server
from pkglib.manage import read_allrevisions_file

import pkglib.testing.pypi

HERE = path.path.getcwd()


def test_develop(pytestconfig):
    """ Creates template, runs setup.py develop then does some checks that the package
        was setup properly.
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='acme.foo', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
            '%s/bin/foo -h' % pkg.virtualenv,
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo'].issrc
        assert installed['acme.bar'].isdev


def test_develop_non_inhouse_namespace(pytestconfig):
    """ As above, using a non-inhouse namespace
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='blackmesa.foobar', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import blackmesa.foobar"' % pkg.python,
            '%s/bin/foobar -h' % pkg.virtualenv,
        ]]
        installed = pkg.installed_packages()
        assert installed['blackmesa.foobar'].issrc
        assert installed['acme.bar'].isdev


def test_develop_final(pytestconfig):
    """ Creates template, runs setup.py develop with the prefer final option
        was setup properly.
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='acme.foo', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q', '--prefer-final'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
            '%s/bin/foo -h' % pkg.virtualenv,
            '%s/bin/python %s/setup.py depgraph -et --boxart' % (pkg.virtualenv, pkg.trunk_dir),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.foo'].issrc
        assert installed['acme.bar'].isrel


def test_test():
    """ Creates template, runs setup.py test (without first running setup.py develop)
    """
    with PkgTemplate(name='acme.foo') as pkg:
        # This one won't run under coverage
        [pkg.run(cmd, capture=False) for cmd in [
            '%s %s/setup.py test' % (pkg.python, pkg.trunk_dir),
        ]]


def test_develop_then_test(pytestconfig):
    """ Creates template, runs setup.py develop then test
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'test'],
                                    pytestconfig, cd=HERE)


def test_test_hudson_mode(pytestconfig):
    """ Creates template, runs setup.py test in hudson mode
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'test', '-H'],
                                    pytestconfig, cd=HERE)


def test_sphinx(pytestconfig):
    """ Creates template, builds doco
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'build_sphinx'],
                                    pytestconfig, cd=HERE)
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc', 'acme.foo.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx', 'html', 'index.html'))


def test_sphinx_multilevel_package(pytestconfig):
    """ Creates template, builds doco for multi-level namespace packages
    """
    with PkgTemplate(name='acme.foo.bar.baz') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'build_sphinx'],
                                    pytestconfig, cd=HERE)
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc', 'acme.foo.bar.baz.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx', 'html', 'index.html'))


def test_sphinx_autodoc_dynamic(pytestconfig):
    """ Creates template, builds doco using dynamic autodoc.
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'build_sphinx', '--autodoc-dynamic'],
                                    pytestconfig, cd=HERE)

        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'docs', 'autodoc', 'acme.foo.rst'))
        assert os.path.isfile(os.path.join(pkg.trunk_dir, 'build', 'sphinx', 'html', 'index.html'))


@pytest.mark.jenkins
def test_jenkins_create(pytestconfig, jenkins_server):
    """ Creates template, creates the jenkins job
    """
    name = 'acme.projecttemplate_test'
    try:
        with PkgTemplate(name=name) as pkg:
            pkg.install_package('pytest-cov')
            print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'jenkins', '--vcs-url=foo',
                                         '--no-prompt', '--server', jenkins_server.uri,
                                         '--user', 'foo', '--password', 'bar'],
                                        pytestconfig, cd=HERE)
        info = jenkins_server.api.get_job_info(name)
        assert info['name'] == name
    finally:
        try:
            jenkins_server.api.delete_job(name)
        except:
            pass


@pytest.mark.jenkins
def test_jenkins_update(pytestconfig, jenkins_server):
    """ Creates template, creates the hudson job, and runs the command again to do an update
    """
    name = 'acme.projecttemplate_test'
    try:
        with PkgTemplate(name=name) as pkg:
            pkg.install_package('pytest-cov')

            jenkins_cmd = ['%s/setup.py' % pkg.trunk_dir, 'jenkins', '--vcs-url=foo',
                           '--no-prompt', '--server', jenkins_server.uri, '--user', 'foo',
                           '--password', 'bar']

            print pkg.run_with_coverage(jenkins_cmd, pytestconfig, cd=HERE)
            print pkg.run_with_coverage(jenkins_cmd, pytestconfig, cd=HERE)

        info = jenkins_server.api.get_job_info(name)
        assert info['name'] == name
    finally:
        try:
            jenkins_server.api.delete_job(name)
        except:
            pass


def test_pyinstall(pytestconfig):
    """ Creates template, runs pyinstall from the setuptools command
    """
    # Find and install latest non-dev version of a given package, and then
    # try and import it
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'pyinstall', 'acme.bar'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.bar"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.bar'].isrel


def test_pyinstall_cmdline(pytestconfig):
    """ As above but running pyinstall from the command-line
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/bin/pyinstall' % pkg.virtualenv, 'acme.bar'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.bar"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.bar'].isrel


# XXX This is broken at the moment
@pytest.mark.skipif('True')
def test_uninstall(pytestconfig):
    """ Creates template, runs easy_install then uninstall
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')

        def do_test(cmd):
            [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
                '%s/bin/easy_install pytz' % (pkg.virtualenv),
                '%s -c "import pytz"' % (pkg.python),
                cmd,
            ]]
            assert 'pytz' not in pkg.installed_packages()

        for cmd in [
            '%s/bin/coverage run -p --source=pkglib %s/setup.py uninstall --yes pytz' %
                    (pkg.virtualenv, pkg.trunk_dir),
            '%s/bin/coverage run -p --source=pkglib %s/bin/pyuninstall --yes pytz' %
                (pkg.virtualenv, pkg.virtualenv),
            ]:
            do_test(cmd)


def test_update(pytestconfig):
    """ Creates template, runs setup.py update
    """
    # TODO: check behaviour
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'update'],
                                    pytestconfig, cd=HERE)


def _svn_info_revision(pkg, workspace, package_name):
    rev_info = pkg.run("svn info %s/%s" % (workspace, package_name), capture=True)
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
            "svn import %s/%s %s -m 'initial import'" % (pkg.workspace, 'acme.foo', pkg.vcs_uri),
            'svn co %s/trunk %s/acme.foo' % (pkg.vcs_uri, workspace.workspace),
        ]]
        print pkg.run_with_coverage(['%s/acme.foo/setup.py' % workspace.workspace, 'egg_info'],
                                    pytestconfig, cd=HERE)
        egg_dir = os.path.join(workspace.workspace, 'acme.foo', 'acme.foo.egg-info')
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
    """ Tests the new-build linking mechanisms, whereby dev builds get their version numbers
        generated on the fly after checking the pypi server for the latest version.
    """
    metadata = dict(
        install_requires='acme.newbuild1',
    )

    def setup_py(pkg, cmd):
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        print pkg.run_with_coverage([pkg.trunk_dir / 'setup.py'] + cmd,
                                    pytestconfig, cd=HERE, env=new_env)

    with pkglib.testing.pypi.create_pkg(pypi_chishop, svn_repo, 'acme.newbuild1', dev=False) as pkg1:
        with pkglib.testing.pypi.create_pkg(pypi_chishop, svn_repo, 'acme.newbuild2',
                                          metadata=metadata, dev=False) as pkg2:
            pkg1.install_package('pytest-cov')
            pkg2.install_package('pytest-cov')

            setup_py(pkg1, ['egg_info', '--new-build'])
            egg_dir = pkg1.trunk_dir / 'acme.newbuild1.egg-info'
            egg_file = egg_dir / 'PKG-INFO'
            assert 'Version: 0.0.dev1' in egg_file.lines(retain=False)

            # Now upload the dev package twice check we get a new build number the next time round
            setup_py(pkg1, ['egg_info', '--new-build', 'bdist_egg', 'upload', '--show-response'])
            setup_py(pkg1, ['egg_info', '--new-build', 'bdist_egg', 'upload', '--show-response'])

            assert 'Version: 0.0.dev2' in egg_file.lines(retain=False)

            # Remove the other package and re-run develop for the second package to get the new dev egg dependency
            setup_py(pkg2, ['uninstall', '-y', 'acme.newbuild1'])
            setup_py(pkg2, ['develop', '-i', '%s/simple' % pypi_chishop.uri])

            # Now make a new build and check the other package is a pinned dependency at the new build number
            setup_py(pkg2, ['egg_info', '--new-build'])
            egg_dir = pkg2.trunk_dir / 'acme.newbuild2.egg-info'
            requires = egg_dir / 'requires.txt'
            assert requires.lines(retain=False) == ['acme.newbuild1==0.0.dev2']


@pytest.mark.chishop
def test_egg_revisions(pypi_chishop, svn_repo, workspace, pytestconfig):
    #pypi_chishop.restore()
    package1_metadata = dict(
        version='1.2.3',
        )

    package2_metadata = dict(
        version='4.5.6',
        install_requires='\n'.join(['acme.er_package1==1.2.3']),
        )

    package3_metadata = dict(
        version='7.8.9',
        install_requires='\n'.join(['acme.er_package2==4.5.6']),
        )

    with pkglib.testing.pypi.create_pkg(pypi_chishop, svn_repo, 'acme.er_package1',
                                     metadata=package1_metadata, dev=False) as pkg1:
        with pkglib.testing.pypi.create_pkg(pypi_chishop, svn_repo, 'acme.er_package2',
                                         metadata=package2_metadata, dev=False) as pkg2:
            with PkgTemplate(name='acme.package3', repo_base=svn_repo.uri, metadata=package3_metadata) as pkg3:
                pkg3.run('%s/bin/easy_install -i %s/simple acme.er_package2' \
                             % (pkg3.virtualenv, pypi_chishop.uri))

                egg_info_dir = pkg3.virtualenv + \
                    '/lib/python2.6/site-packages/acme.er_package2-4.5.6-py2.6.egg/EGG-INFO'
                all_revisions_fname = os.path.join(egg_info_dir, 'allrevisions.txt')

                assert os.path.isfile(all_revisions_fname)
                name_to_revno = {}

                for rev_data in read_allrevisions_file(all_revisions_fname):
                    # name => revision
                    name_to_revno[rev_data[0]] = str(rev_data[3])

                assert len(name_to_revno) == 2
                assert name_to_revno['acme.er_package1'] == _svn_info_revision(pkg3, pkg1.workspace, 'acme.er_package1')
                assert name_to_revno['acme.er_package2'] == _svn_info_revision(pkg3, pkg2.workspace, 'acme.er_package2')


def test_cython_build_ext(pytestconfig):
    """ Creates template, runs setup.py develop which will invoke build_ext which for this
        project template contains cython template files
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'cython')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
        ]]
        assert pkg.run('%s -c "from acme.foo import _mycython; print _mycython.test_cython([1,2,3])"' %
                pkg.python, capture=True).strip() == "[2, 4, 6]"


def test_cython_build_ext_cpp(pytestconfig):
    """ Creates template, runs setup.py develop which will invoke build_ext which for this
        project template contains cython template files for C++
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'cython_cpp')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop'],
                                    pytestconfig, cd=HERE)
        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.foo"' % pkg.python,
        ]]
        assert pkg.run('%s -c "from acme.foo import _cppcython; print _cppcython.test_cpp_cython([1,2,3,4])"' %
                pkg.python, capture=True).strip() == "[0.5, 1.0, 1.5, 2.0]"


def test_ext_gcov_test(pytestconfig):
    """Create a package with a Python extension we can run ext_gcov_test on
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'gcov_ext')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        pkg.run_with_coverage([os.path.join(pkg.trunk_dir, 'setup.py'), 'ext_gcov_test'],
                              pytestconfig, cd=pkg.trunk_dir)
        root = etree.parse(os.path.join(pkg.trunk_dir, 'gcov', 'coverage.xml'))
        (class_,) = root.findall('./packages/package/classes/class')
        assert class_.attrib['filename'] == 'src/ext.c'
        lines = dict((int(e.attrib['number']), int(e.attrib['hits'])) for e in class_.findall('./lines/line'))
        assert lines[4] >= 1    # fn_1 covered
        assert lines[8] == 0    # fn_2 not covered


def test_ext_gcov_test_cython(pytestconfig):
    """Create a package with a Cython extension we can run ext_gcov_test on
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'gcov_ext_cython')
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        copy_tree(test_dir, pkg.trunk_dir)
        pkg.run_with_coverage([os.path.join(pkg.trunk_dir, 'setup.py'), 'ext_gcov_test'],
                              pytestconfig, cd=pkg.trunk_dir)
        root = etree.parse(os.path.join(pkg.trunk_dir, 'gcov', 'coverage.xml'))
        (class_,) = root.findall('./packages/package/classes/class')
        assert class_.attrib['filename'] == 'src/ext.pyx'
        lines = dict((int(e.attrib['number']), int(e.attrib['hits'])) for e in class_.findall('./lines/line'))
        assert lines[5] >= 1    # fn_1 covered
        assert lines[12] == 0   # fn_2 not covered


def strip(arr):
    for i in range(len(arr)):
        arr[i] = arr[i].strip()

def test_deploy(pytestconfig):
    """ Creates template, runs setup.py deploy
    """
    cfg = dict(deploy=dict(
        enabled='1',
        console_scripts='\n'.join([
                'python',
                'foo',
        ]),
    ))
    with PkgTemplate(name='acme.foo', **cfg) as pkg:
        install_dir = os.path.join(pkg.workspace, 'install')
        bin_dir = os.path.join(install_dir, 'bin')
        pkg_dir = os.path.join(install_dir, 'packages')
        os.mkdir(install_dir)
        os.mkdir(bin_dir)
        os.mkdir(pkg_dir)
        pkg.install_package('pytest-cov')
        new_env = copy.copy(pkg.env)
        new_env['PYTHON_RESEARCH_APPS'] = install_dir
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, env=new_env, cd=HERE)

        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'deploy'],
                                    pytestconfig, env=new_env, cd=HERE)

        assert os.path.islink(os.path.join(bin_dir, 'python'))
        assert os.path.islink(os.path.join(bin_dir, 'foo'))
        assert os.path.isfile(os.path.join(pkg_dir, 'acme.foo', '1.0.0.dev1', 'bin', 'foo'))


def test_depgraph(pytestconfig):
    """ Creates template, runs setup.py depgraph
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'develop', '-q'],
                                    pytestconfig, cd=HERE)
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'depgraph'],
                                    pytestconfig, cd=HERE)


def test_cleanup(pytestconfig):
    """ Creates template, adds some stuff into site-packages then runs setup.py cleanup / pycleanup
    """
    metadata = dict(
        install_requires='acme.bar',
    )
    with PkgTemplate(name='acme.foo', metadata=metadata) as pkg:
        pkg.install_package('pytest-cov')

        def do_test(cleanup_cmd):
            site_packages = pkg.virtualenv / 'lib' / ('python%d.%d' % sys.version_info[:2]) / 'site-packages'
            contents = set(site_packages.listdir())
            print "old contents: %r" % contents
            [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
                'mkdir %s/bad-1.3.egg' % site_packages,
                'mkdir %s/xyz-2.0.egg' % site_packages,
                '> %s/blah.py' % site_packages,
                '> %s/zipped-2.0.egg' % site_packages,
            ]]
            print pkg.run_with_coverage(cleanup_cmd, pytestconfig, cd=HERE)
            print "new contents: %r" % site_packages.listdir()
            expected = set(contents)
            expected.add('%s/blah.py' % site_packages)  # this python file should be left alone
            assert set(site_packages.listdir()) == expected

        for cleanup_cmd in [
            # run via setup.py
            ['%s/setup.py' % pkg.trunk_dir, 'cleanup'],
            # run via cmdline pycleanup
            ['%s/bin/pycleanup' % pkg.virtualenv],
            ]:
            do_test(cleanup_cmd)


def test_test_egg(pytestconfig):
    """ Creates template, runs setup.py test_egg
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'test_egg'],
                                    pytestconfig, cd=HERE)
        egg = path.path(pkg.trunk_dir) / 'dist' / 'test.acme.foo-1.0.0.dev1-py2.6.egg'
        assert egg.isfile()

        # Now install it and run the tests
        pkg.run('%s/bin/easy_install %s' % (pkg.virtualenv, egg))

        # XXX stripping coverage/pylint off for now, fix this later - it should work
        new_env = copy.copy(pkg.env)
        if 'BUILD_TAG' in new_env:
            del(new_env['BUILD_TAG'])
        pkg.run_with_coverage(['%s/bin/runtests' % (pkg.virtualenv), 'acme.foo'],
                              pytestconfig, cd=HERE, env=new_env)


EXT_SETUP_CFG = """
from pkglib.setuptools.command.release_externals import release_externals
from pkglib.setuptools import setup
class MyCommand(release_externals):
    def run(self):
        raise SystemExit(37)
setup(cmdclass={'release_externals': MyCommand})
"""


def test_release_externals(pytestconfig):
    """ Create a package with a custom release externals hook
    """
    with PkgTemplate(name='acme.foo') as pkg:
        pkg.install_package('pytest-cov')
        (path.path(pkg.trunk_dir) / 'setup.py').write_text(EXT_SETUP_CFG)
        pkg.run('%s %s/setup.py develop -q' % (pkg.python, pkg.trunk_dir))
        with pytest.raises(subprocess.CalledProcessError) as e:
            print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'release_externals'],
                                        pytestconfig, cd=HERE)
        assert e.value.returncode == 37
