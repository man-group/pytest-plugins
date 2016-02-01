import json


def test_server(devpi_server):
    res = devpi_server.api('getjson', '/{}/{}'.format(devpi_server.user, devpi_server.index))
    assert json.loads(res) == {
        "result": {
            "acl_upload": [
                "testuser"
            ],
            "bases": [],
            "projects": [],
            "pypi_whitelist": [],
            "type": "stage",
            "volatile": True
        },
        "type": "indexconfig"
    }


def test_upload(devpi_server):
    pkg_dir = devpi_server.workspace / 'pkg'
    pkg_dir.mkdir_p()
    setup_py = pkg_dir / 'setup.py'
    setup_py.write_text("""
from setuptools import setup
setup(name='test-foo',
      version='1.2.3')
""")
    pkg_dir.chdir()
    devpi_server.api('upload')
    res = devpi_server.api('getjson', '/{}/{}'.format(devpi_server.user, devpi_server.index))
    assert json.loads(res)['result']['projects'] == ['test-foo']
