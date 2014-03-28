import copy
import os.path
import sys
import tarfile
import marshal
import imp
import struct
import types
from datetime import datetime
from zipfile import ZipFile
from io import BytesIO
from contextlib import closing
from subprocess import CalledProcessError

import pytest

from pkglib_util.six.moves import urlopen  # @UnresolvedImport

from pkglib.pypi.pypirc import PyPiRc
from pkglib.pypi.xmlrpc import XMLRPCPyPIAPI
from pkglib.errors import UserError
from pkglib_testing.util import PkgTemplate, update_setup_cfg
from pkglib_testing.pytest.pypi import pypi_chishop, pypi_chishop_with_egg_cache  # @UnusedImport # NOQA
from pkglib_testing.pytest.util import workspace  # @UnusedImport # NOQA

HERE = os.getcwd()


def test_resolve_dashed_name():
    """ Tests resolving packages with dashes in the name using PyPI API
    """
    pypi = XMLRPCPyPIAPI()
    assert pypi.resolve_dashed_name('foo') == 'foo'
    assert pypi.resolve_dashed_name('acme-data.foobar') == 'acme_data.foobar'
    assert pypi.resolve_dashed_name('pytest-cov') == 'pytest-cov'



@pytest.mark.chishop
def test_upload(pytestconfig, pypi_chishop):
    """Test we can upload packages to an instance of chishop PyPI.
        This also covers the setuptools extensions register and upload.
    """
    with PkgTemplate(name='acme.tpi.test.upload-1.0.0.dev1') as pkg:
        pkg.create_pypirc(pypi_chishop.get_rc())
        pkg.install_package('pytest-cov')
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = ['%s/setup.py' % pkg.trunk_dir]
        setup_cmd += ['sdist', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)
    dist_location = ('chishop/media/dists/a/acme.tpi.test.upload'
                     '/acme.tpi.test.upload-1.0.0.dev1.tar.gz')
    assert os.path.isfile(os.path.join(pypi_chishop.workspace, dist_location))

    dist_url = ('http://%s:%s/media/dists/a/acme.tpi.test.upload'
                '/acme.tpi.test.upload-1.0.0.dev1.tar.gz'
                % (pypi_chishop.hostname, pypi_chishop.port))
    response = urlopen(dist_url)
    buf = response.read()
    fh = BytesIO(buf)
    with closing(tarfile.open(fileobj=fh)) as tf:
        assert 'acme.tpi.test.upload-1.0.0.dev1/PKG-INFO' in tf.getnames()


def _add_ext_module(pkg):
    setup_py = '%s/setup.py' % pkg.trunk_dir
    with open(setup_py, 'w') as f:
        f.write("""from pkglib.setuptools import setup
from pkglib.setuptools import Distribution as _Distribution
class Distribution(_Distribution):
    def has_ext_modules(self):
        return True
setup(distclass=Distribution)
""")


@pytest.mark.chishop
def test_upload_different_platforms(pytestconfig, pypi_chishop):
    with PkgTemplate(name='acme.tpi.test.platforms') as pkg:
        pkg.create_pypirc(pypi_chishop.get_rc())
        pkg.install_package('pytest-cov')
        setup_py = '%s/setup.py' % pkg.trunk_dir
        _add_ext_module(pkg)
        setup_cmd = [setup_py, 'bdist_egg', '-p', 'platform1', 'register', 'upload']
        pkg.run_with_coverage(setup_cmd, pytestconfig, env=dict(pkg.env, HOME=pkg.workspace),
                              cd=HERE, capture_stdout=False)

        setup_cmd = [setup_py, 'bdist_egg', '-p', 'platform2', 'register', 'upload']
        pkg.run_with_coverage(setup_cmd, pytestconfig, env=dict(pkg.env, HOME=pkg.workspace),
                              cd=HERE, capture_stdout=False)

    response = urlopen('http://%s:%s/simple/acme.tpi.test.platforms' %
                       (pypi_chishop.hostname, pypi_chishop.port))
    buf = response.read()
    pyversion = sys.version[:3]  # sysconfig.get_python_version()
    assert ('acme.tpi.test.platforms-1.0.0.dev1-py%s-platform1.egg' % pyversion) in buf
    assert ('acme.tpi.test.platforms-1.0.0.dev1-py%s-platform2.egg' % pyversion) in buf


@pytest.mark.chishop
def test_prevent_upload_after_adding_platform(pytestconfig, pypi_chishop):
    """If the maintainer makes the package platform-aware (e.g. by Cythonising), we should refuse
    upload without a version bump."""
    expected_msg = ('Upload failed (400): BAD REQUEST: cannot upload a platform-specific '
                    'distribution when a platform-independent distribution already exists '
                    '(delete the existing distribution, or bump the version)')

    with PkgTemplate(name='acme.tpi.test.cythonise') as pkg:
        pkg.create_pypirc(pypi_chishop.get_rc())
        pkg.install_package('pytest-cov')
        setup_py = '%s/setup.py' % pkg.trunk_dir

        setup_cmd = [setup_py, 'bdist_egg', 'register', 'upload']
        pkg.run_with_coverage(setup_cmd, pytestconfig, env=dict(pkg.env, HOME=pkg.workspace),
                              cd=HERE, capture_stdout=False)

        _add_ext_module(pkg)
        setup_cmd = [setup_py, 'bdist_egg', '-p', 'platform1', 'register', 'upload']
        with pytest.raises(CalledProcessError) as exc:
            print(pkg.run_with_coverage(setup_cmd, pytestconfig,
                                        env=dict(pkg.env, HOME=pkg.workspace),
                                        cd=HERE, capture_stderr=True))
    assert expected_msg in exc.value.output


@pytest.mark.chishop
def test_prevent_upload_after_removing_platform(pytestconfig, pypi_chishop):
    """If the maintainer makes the package non-platform-aware (e.g. by de-Cythonising), we should
    refuse upload without a version bump."""
    expected_msg = ('Upload failed (400): BAD REQUEST: cannot upload a platform-independent '
                    'distribution when a platform-specific distribution already exists '
                    '(delete the existing distribution, or bump the version)')

    with PkgTemplate(name='acme.tpi.test.decythonise') as pkg:
        pkg.create_pypirc(pypi_chishop.get_rc())
        pkg.install_package('pytest-cov')
        setup_py = '%s/setup.py' % pkg.trunk_dir

        _add_ext_module(pkg)
        setup_cmd = [setup_py, 'bdist_egg', '-p', 'platform1', 'register', 'upload']
        pkg.run_with_coverage(setup_cmd, pytestconfig, env=dict(pkg.env, HOME=pkg.workspace),
                              cd=HERE, capture_stdout=False)

        with open(setup_py, 'w') as f:
            f.write("from pkglib.setuptools import setup\nsetup()")
        setup_cmd = [setup_py, 'bdist_egg', 'register', 'upload']
        with pytest.raises(CalledProcessError) as exc:
            print(pkg.run_with_coverage(setup_cmd, pytestconfig,
                                        env=dict(pkg.env, HOME=pkg.workspace),
                                        cd=HERE, capture_stderr=True))
    assert expected_msg in exc.value.output


@pytest.mark.chishop
def test_delete_other_dev_eggs(pytestconfig, pypi_chishop):
    with PkgTemplate(name='acme.tpi.test.dev-1.0.0.dev1') as pkg:
        dist_dir = os.path.join(pypi_chishop.workspace, 'chishop/media/dists/a/acme.tpi.test.dev')
        pkg.create_pypirc(pypi_chishop.get_rc())
        pkg.install_package('pytest-cov')
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = ['%s/setup.py' % pkg.trunk_dir]
        setup_cmd += ['sdist', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)
        assert os.path.isfile(os.path.join(dist_dir, 'acme.tpi.test.dev-1.0.0.dev1.tar.gz'))

        update_setup_cfg('%s/setup.cfg' % pkg.trunk_dir, vcs_uri=pkg.vcs_uri,
                         metadata={'version': '1.1.0'}, dev=True)
        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)
        assert os.path.isfile(os.path.join(dist_dir, 'acme.tpi.test.dev-1.1.0.dev1.tar.gz'))
        assert not os.path.isfile(os.path.join(dist_dir, 'acme.tpi.test.dev-1.0.0.dev1.tar.gz'))


@pytest.mark.chishop
def test_validate_credentials(pypi_chishop, workspace):
    workspace.create_pypirc(pypi_chishop.get_rc())
    pypirc = PyPiRc(os.path.join(workspace.workspace, '.pypirc'))
    pypirc.validate_credentials(pypi_chishop.uri)


@pytest.mark.chishop
def test_validate_credentials_raises_user_error_on_unauthorized(pypi_chishop,
                                                                workspace):
    config = pypi_chishop.get_rc()
    config.set('server-login', 'password', 'hunter2')
    workspace.create_pypirc(config)
    pypirc = PyPiRc(os.path.join(workspace.workspace, '.pypirc'))
    with pytest.raises(UserError) as exc:
        pypirc.validate_credentials(pypi_chishop.uri)
    assert exc.value.msg.startswith(UserError('Invalid PyPi credentials',
                                              pypi_chishop.uri, '').msg)


def pyinstall_cmd_func(pkg, cmd, run_from):
    if run_from == 'cmdline':
        return [os.path.join(os.path.dirname(pkg.python), cmd)]
    elif run_from == 'setuptools':
        return [os.path.join(pkg.trunk_dir, "setup.py"), cmd]
    else:
        raise ValueError(run_from)


@pytest.mark.parametrize(('run_from',), [('cmdline',), ('setuptools',)])
def test_pyinstall__fetches_package_from_pypi(pytestconfig, pypi_chishop,
                                              run_from):
    """ Creates template, runs pyinstall from the setuptools command
    Find and install latest non-dev version of a given package, and then
    try and import it
    """
    pypi_url = "http://%s:%s/simple" % (pypi_chishop.hostname,
                                        pypi_chishop.port)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop.get_rc())
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = [os.path.join(pkg.trunk_dir, "setup.py")]
        setup_cmd += ['bdist_egg', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)

        pyinstall_cmd = pyinstall_cmd_func(pkg, 'pyinstall', run_from)
        pyinstall_cmd = pyinstall_cmd + ['-i', pypi_url, 'acme.pypipkg']

        pkg.run_with_coverage(pyinstall_cmd, pytestconfig, cd=HERE, capture_stdout=False)

        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.pypipkg"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.pypipkg'].version == '1.2.3'
        assert installed['acme.pypipkg'].isrel


@pytest.mark.chishop
@pytest.mark.skipif('".".join(str(v) for v in sys.version_info[:3]) '
                    'not in os.environ[PYTHON_VERSIONS_ENV_VAR]')
def test_egg_cache_updated_on_upload(pytestconfig, pypi_chishop_with_egg_cache):
    cache = pypi_chishop_with_egg_cache.egg_cache
    dev_cache = pypi_chishop_with_egg_cache.dev_egg_cache
    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop_with_egg_cache.get_rc())

        pkg.run_with_coverage([os.path.join(pkg.trunk_dir, "setup.py"),
                               'bdist_egg', 'register', 'upload',
                               '--show-response'], pytestconfig,
                              env=dict(pkg.env, HOME=pkg.workspace), cd=HERE, capture_stdout=False)
        egg = 'acme.pypipkg-1.2.3-py%d.%d.egg' % sys.version_info[:2]
        assert os.path.exists(os.path.join(cache, 'ap', egg))
        assert not os.path.exists(os.path.join(dev_cache, 'ap', egg))
        py, pyc = (os.path.join('acme', 'pypipkg', '__init__.' + ext)
                   for ext in ('py', 'pyc'))
        with closing(ZipFile(os.path.join(cache, 'ap', egg))) as z:
            f = z.open(pyc)
            magic = f.read(4)
            stamp = struct.unpack('<L', f.read(4))[0]
            code = marshal.loads(f.read())  # remainder of the file
            assert magic == imp.get_magic()
            assert (datetime.fromtimestamp(stamp) ==
                    datetime(*z.getinfo(py).date_time))
            assert isinstance(code, types.CodeType)
            assert code.co_filename == os.path.join(cache, 'ap', egg, py)


@pytest.mark.chishop
@pytest.mark.skipif('".".join(str(v) for v in sys.version_info[:3]) '
                    'not in os.environ[PYTHON_VERSIONS_ENV_VAR]')
def test_egg_caches_not_updated_on_upload_of_dev1_egg(pytestconfig, pypi_chishop_with_egg_cache):
    cache = pypi_chishop_with_egg_cache.egg_cache
    dev_cache = pypi_chishop_with_egg_cache.dev_egg_cache
    with PkgTemplate(name="acme.pypipkg", dev=True,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop_with_egg_cache.get_rc())

        pkg.run_with_coverage([os.path.join(pkg.trunk_dir, "setup.py"),
                               'bdist_egg', 'register', 'upload',
                               '--show-response'], pytestconfig,
                              env=dict(pkg.env, HOME=pkg.workspace), cd=HERE, capture_stdout=False)
        egg = 'acme.pypipkg-1.2.3.dev1-py%d.%d.egg' % sys.version_info[:2]
        assert not os.path.exists(os.path.join(cache, 'ap', egg))
        assert not os.path.exists(os.path.join(dev_cache, 'ap', egg))


@pytest.mark.chishop
@pytest.mark.skipif('".".join(str(v) for v in sys.version_info[:3]) '
                    'not in os.environ[PYTHON_VERSIONS_ENV_VAR]')
def test_dev_egg_cache_updated_on_upload_of_dev1rXXXX_egg(pytestconfig,
                                                          pypi_chishop_with_egg_cache):
    cache = pypi_chishop_with_egg_cache.egg_cache
    dev_cache = pypi_chishop_with_egg_cache.dev_egg_cache
    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3.dev1-r184247")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop_with_egg_cache.get_rc())

        pkg.run_with_coverage([os.path.join(pkg.trunk_dir, "setup.py"),
                               'bdist_egg', 'register', 'upload',
                               '--show-response'], pytestconfig,
                              env=dict(pkg.env, HOME=pkg.workspace), cd=HERE, capture_stdout=False)
        egg = 'acme.pypipkg-1.2.3.dev1_r184247-py%d.%d.egg' % sys.version_info[:2]

        assert not os.path.exists(os.path.join(cache, 'ap', egg))
        assert os.path.exists(os.path.join(dev_cache, 'ap', egg))
        py, pyc = (os.path.join('acme', 'pypipkg', '__init__.' + ext)
                   for ext in ('py', 'pyc'))
        with closing(ZipFile(os.path.join(dev_cache, 'ap', egg))) as z:
            f = z.open(pyc)
            magic = f.read(4)
            stamp = struct.unpack('<L', f.read(4))[0]
            code = marshal.loads(f.read())  # remainder of the file
            assert magic == imp.get_magic()
            assert (datetime.fromtimestamp(stamp) ==
                    datetime(*z.getinfo(py).date_time))
            assert isinstance(code, types.CodeType)
            assert code.co_filename == os.path.join(dev_cache, 'ap', egg, py)


@pytest.mark.parametrize(('run_from',), [('cmdline',), ('setuptools',)])
def test_pyinstall_links_to_package_from_cache_in_preference_to_fetching_from_pypi(
        pytestconfig,
        pypi_chishop_with_egg_cache,
        run_from):
    """ Creates template, runs pyinstall from the setuptools command
    Find and install latest non-dev version of a given package, and then
    try and import it, check that it is an egglink into the egg cache.
    """

    cache = pypi_chishop_with_egg_cache.egg_cache

    pypi_url = "http://%s:%s/simple" % (pypi_chishop_with_egg_cache.hostname,
                                        pypi_chishop_with_egg_cache.port)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop_with_egg_cache.get_rc())
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = [os.path.join(pkg.trunk_dir, "setup.py")]
        setup_cmd += ['bdist_egg', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)

        path_of_egg_in_cache = os.path.join(cache, 'ap', ('acme.pypipkg-1.2.3-py%d.%d.egg' %
                                                          sys.version_info[:2]))
        assert os.path.exists(path_of_egg_in_cache)

        pyinstall_cmd = pyinstall_cmd_func(pkg, 'pyinstall', run_from)
        pyinstall_cmd = pyinstall_cmd + ['-i', pypi_url, 'acme.pypipkg']

        pkg.run_with_coverage(pyinstall_cmd, pytestconfig, cd=HERE,
                              env={'VIRTUALENV_SEARCH_PATH': cache}, capture_stdout=False)

        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.pypipkg"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.pypipkg'].version == '1.2.3'
        assert installed['acme.pypipkg'].isrel
        assert installed['acme.pypipkg'].source_path == path_of_egg_in_cache


def test_easyinstall_command_fetches_package_from_pypi(pytestconfig, pypi_chishop):
    """ Creates template, runs easy_install from the setuptools command
    Find and install latest non-dev version of a given package, and then
    try and import it
    """
    pypi_url = "http://%s:%s/simple" % (pypi_chishop.hostname,
                                        pypi_chishop.port)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop.get_rc())
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = [os.path.join(pkg.trunk_dir, "setup.py")]
        setup_cmd += ['bdist_egg', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')

        easyinstall_cmd = [os.path.join(pkg.trunk_dir, "setup.py"),
                           "easy_install", '-i', pypi_url, "acme.pypipkg"]

        pkg.run_with_coverage(easyinstall_cmd, pytestconfig, cd=HERE, capture_stdout=False)

        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.pypipkg"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.pypipkg'].version == '1.2.3'
        assert installed['acme.pypipkg'].isrel


def test_easyinstall_command_links_to_package_from_cache_in_preference_to_fetching_from_pypi(
        pytestconfig,
        pypi_chishop_with_egg_cache):
    """ Creates template, runs easy_install from the setuptools command
    Find and install latest non-dev version of a given package, and then
    try and import it, check that it is an egglink into the egg cache.
    """

    cache = pypi_chishop_with_egg_cache.egg_cache

    pypi_url = "http://%s:%s/simple" % (pypi_chishop_with_egg_cache.hostname,
                                        pypi_chishop_with_egg_cache.port)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop_with_egg_cache.get_rc())
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = [os.path.join(pkg.trunk_dir, "setup.py")]
        setup_cmd += ['bdist_egg', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)

        path_of_egg_in_cache = os.path.join(cache, 'ap', ('acme.pypipkg-1.2.3-py%d.%d.egg' %
                                                          sys.version_info[:2]))
        assert os.path.exists(path_of_egg_in_cache)

    with PkgTemplate(name="acme.pypipkg", dev=False,
                     metadata=dict(name="acme.pypipkg", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')

        easyinstall_env = {}
        easyinstall_env['VIRTUALENV_SEARCH_PATH'] = cache

        easyinstall_cmd = [os.path.join(pkg.trunk_dir, "setup.py"),
                           "easy_install", '-i', pypi_url, "acme.pypipkg"]

        pkg.run_with_coverage(easyinstall_cmd, pytestconfig, cd=HERE, env=easyinstall_env,
                              capture_stdout=False)

        [pkg.run(cmd, capture=False, cd=HERE) for cmd in [
            '%s -c "import acme.pypipkg"' % (pkg.python),
        ]]
        installed = pkg.installed_packages()
        assert installed['acme.pypipkg'].version == '1.2.3'
        assert installed['acme.pypipkg'].isrel
        assert installed['acme.pypipkg'].source_path == path_of_egg_in_cache


def test_pyuninstall(pytestconfig, pypi_chishop):
    """ Creates template, runs pyinstall
    Find and install latest non-dev version of a given package, and then
    try and import it. Finally uninstall it and show it has gone.
    """
    pypi_url = "http://%s:%s/simple" % (pypi_chishop.hostname,
                                        pypi_chishop.port)

    with PkgTemplate(name="acme.bar", dev=False,
                     metadata=dict(name="acme.bar", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')
        pkg.create_pypirc(pypi_chishop.get_rc())
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        setup_cmd = [os.path.join(pkg.trunk_dir, "setup.py"),
                     'bdist_egg', 'register', 'upload', '--show-response']

        pkg.run_with_coverage(setup_cmd, pytestconfig, env=new_env, cd=HERE, capture_stdout=False)

    with PkgTemplate(name="acme.foo", dev=False,
                     metadata=dict(name="acme.foo", version="1.2.3")) as pkg:
        pkg.install_package('pytest-cov')

        pyinstall_cmd = [os.path.join(os.path.dirname(pkg.python), 'pyinstall'),
                         '-i', pypi_url, 'acme.bar']
        pkg.run_with_coverage(pyinstall_cmd, pytestconfig, cd=HERE, capture_stdout=False)
        assert 'acme.bar' in pkg.installed_packages()

        pyuninstall_cmd = [os.path.join(os.path.dirname(pkg.python), 'pyuninstall'),
                           '--yes', 'acme.bar']
        pkg.run_with_coverage(pyuninstall_cmd, pytestconfig, cd=HERE, capture_stdout=False)
        assert 'acme.bar' not in pkg.installed_packages()
