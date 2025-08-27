import gc
import os
import pytest


from pytest_shutil.env import set_env
from pytest_server_fixtures.xvfb import XvfbServer


class _TestQtApp(object):
    app = None


TestQtApp = _TestQtApp()


@pytest.fixture(scope="session")
def q_application():
    """ Initialise a QT application with a Xvfb server
    """
    try:
        from PyQt4 import QtGui
    except ImportError:
        pytest.skip('PyQT4 not installed, skipping test')

    global TestQtApp
    assert hasattr(TestQtApp, 'app'), "Can only initialize QApplication once per process"

    if TestQtApp.app is None:
        # TODO: investigate if this is still the case, if not just use the regular xvfb_server fixture
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
