import gc
import os
import pytest

from PyQt4 import QtGui

from ahl.testing.util import set_env
from ahl.testing.xvfb_server import XvfbServer


class _TestQtApp(object):
    app = None


TestQtApp = _TestQtApp()


@pytest.yield_fixture(scope="session", autouse=True)
def q_application():
    global TestQtApp
    assert hasattr(TestQtApp, 'app'), "Can only initialize QApplication once per process"

    if TestQtApp.app is None:
        if 'PYDEV_CONSOLE_ENCODING' in os.environ:
            # PyDev destroys session scoped fixtures after each test, so we can't clean up the XvfbServer
            global server
            server = XvfbServer()
            with set_env(XAUTHORITY=server.authfile, DISPLAY=server.display):
                TestQtApp.app = QtGui.QApplication([__name__, '-display', server.display])
            yield TestQtApp
        else:
            with XvfbServer() as server:
                with set_env(XAUTHORITY=server.authfile, DISPLAY=server.display):
                    TestQtApp.app = QtGui.QApplication([__name__, '-display', server.display])
                yield TestQtApp
                TestQtApp.app.exit()
                del TestQtApp.app
                gc.collect()

    else:
        yield TestQtApp
