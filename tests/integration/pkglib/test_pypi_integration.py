import os.path
import copy

from pkglib.pypi.xmlrpc import XMLRPCPyPIAPI

from pkglib.testing.util import PkgTemplate

HERE = os.getcwd()


def test_upload(pytestconfig, pypi):
    """Test we can upload packages to an instance of chishop PyPI.
        This also covers the setuptools extensions register and upload.
    """
    #pypi_chishop.restore()
    with PkgTemplate(name='acme.tpi_test_upload') as pkg:
        pkg.create_pypirc(pypi.get_rc())
        pkg.install_package('pytest-cov')
        new_env = copy.copy(pkg.env)
        new_env['HOME'] = pkg.workspace
        print pkg.run_with_coverage(['%s/setup.py' % pkg.trunk_dir, 'sdist', 'register',
                               'upload', '--show-response'],
                              pytestconfig, env=new_env, cd=HERE)
    assert os.path.isfile(os.path.join(pypi.workspace, 'chishop/media/dists/a/acme.tpi_test_upload/acme.tpi_test_upload-1.0.0.dev1.tar.gz'))

    import tarfile, urllib2, cStringIO
    dist_url = 'http://%s:%s/media/dists/a/acme.tpi_test_upload/acme.tpi_test_upload-1.0.0.dev1.tar.gz' % (pypi_chishop.hostname, pypi_chishop.port)
    response = urllib2.urlopen(dist_url)
    buf = response.read()
    fh = cStringIO.StringIO(buf)
    try:
        tf = tarfile.open(fileobj=fh)
        assert 'acme.tpi_test_upload-1.0.0.dev1/PKG-INFO' in tf.getnames()
    finally:
        tf.close()


def test_resolve_dashed_name():
    """ Tests resolving packages with dashes in the name using PyPI API
    """
    pypi = XMLRPCPyPIAPI()
    assert pypi.resolve_dashed_name('foo') == 'foo'
    assert pypi.resolve_dashed_name('acme-data.foobar') == 'acme_data.foobar'
    assert pypi.resolve_dashed_name('pytest-cov') == 'pytest-cov'
