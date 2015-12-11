import os

from pytest_pyramid_server import InlinePyramidTestServer

CONFIG_DIR = os.path.dirname(__file__) + '/config'


def test_InlinePyramidTestServer():
    ipts = InlinePyramidTestServer(config_dir=CONFIG_DIR)
    ipts.start()
    assert ipts.check_server_up()
    ipts.kill()
    assert not ipts.check_server_up()
