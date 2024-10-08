import json
import os
from pathlib import Path

NEW_INDEX = {
    u"result": {
        u"acl_toxresult_upload": [u":ANONYMOUS:"],
        u"acl_upload": [u"testuser"],
        u"bases": [],
        u"mirror_whitelist": [],
        u"mirror_whitelist_inheritance": u"intersection",
        u"projects": [],
        u"type": u"stage",
        u"volatile": True,
    },
    u"type": u"indexconfig",
}


def test_server(devpi_server):
    res = devpi_server.api(
        "getjson", "/{}/{}".format(devpi_server.user, devpi_server.index)
    )
    assert json.loads(res) == NEW_INDEX


def test_upload(devpi_server):
    pkg_dir: Path = devpi_server.workspace / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    setup_py = pkg_dir / "setup.py"
    setup_py.write_text(
        """
from setuptools import setup
setup(name='test-foo',
      version='1.2.3')
"""
    )
    orig_dir = os.getcwd()
    try:
        os.chdir(pkg_dir)
        devpi_server.api("upload")
        res = devpi_server.api(
            "getjson", "/{}/{}".format(devpi_server.user, devpi_server.index)
        )
        assert json.loads(res)["result"]["projects"] == ["test-foo"]
    finally:
        os.chdir(orig_dir)


def test_function_index(devpi_server, devpi_function_index):
    res = devpi_server.api(
        "getjson", "/{}/test_function_index".format(devpi_server.user)
    )
    assert json.loads(res) == NEW_INDEX
