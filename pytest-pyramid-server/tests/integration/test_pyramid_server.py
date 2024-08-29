import os

from pytest_pyramid_server import InlinePyramidTestServer, PyramidTestServer

CONFIG_DIR = os.path.dirname(__file__) + '/config'


def test_InlinePyramidTestServer():
    ipts = InlinePyramidTestServer(config_dir=CONFIG_DIR)
    ipts.start()
    assert ipts.check_server_up()
    ipts.kill()
    assert not ipts.check_server_up()


def test_PyramidTestServer():
    pts = PyramidTestServer(config_dir=CONFIG_DIR)
    pts.start()
    assert pts.check_server_up()
    pts.kill()
    assert not pts.check_server_up()
