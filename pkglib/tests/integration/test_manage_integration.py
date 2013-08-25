import os.path
import pytest

from pkglib import manage
from pkglib_testing.pypi import create_pkg
from pkglib_testing.pytest.util import pytest_funcarg__svn_repo, pytest_funcarg__workspace, Workspace


class Options(object):
    """ mock options object """
    verbose = True


def test_checkout(pypi, svn_repo, workspace):
    """ Creates a new package from the template, imports it into a test repo.
        Tests checking it out by name
    """
    #pypi_chishop.restore()
    with create_pkg(pypi, svn_repo, 'acme.tmi_test_checkout'):
        manage.checkout_pkg(workspace.workspace, pypi.api, 'acme.tmi_test_checkout',
                            Options(), 'trunk')
        assert os.path.isfile(os.path.join(workspace.workspace, 'setup.py'))


def test_create_virtualenv():
    with Workspace() as workspace:
        manage.create_virtualenv(os.path.join(workspace.workspace, 'foo'))
        assert os.path.isfile(os.path.join(workspace.workspace, 'foo',
                                            'bin', 'python'))


def test_install_pkg():
    with Workspace() as workspace:
        manage.create_virtualenv(os.path.join(workspace.workspace))
        manage.install_pkg(workspace.workspace, 'simplejson')
        assert 'simplejson' in manage.run(
            [(os.path.join(workspace.workspace, 'bin', 'pip')), 'freeze'],
             capture_stdout=True)


@pytest.mark.skipif("True")
def test_get_pkg_description():
    with Workspace() as workspace:
        with manage.chdir(workspace.workspace):
            # README.txt only
            with open('README.txt', 'w') as fp:
                fp.write('README\n')
            assert manage.get_pkg_description({}) == 'README\n\n\n'
            # README.txt plus CHANGES.txt
            with open('CHANGES.txt', 'w') as fp:
                fp.write('CHANGES\n')
            assert manage.get_pkg_description({}) == 'README\n\n\nCHANGES\n'
            # Just CHANGES.txt, pulling README from the package
            os.unlink('README.txt')
            with open('foo.py', 'w') as fp:
                fp.write('"""\nFOO\n"""\n')
            sys.path.append(workspace.workspace)
            assert manage.get_pkg_description({'name': 'foo'}) == '\nFOO\n\n\nCHANGES\n'
