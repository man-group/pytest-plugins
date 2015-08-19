from PyQt4 import QtGui

def test_q_application(q_application):
    assert QtGui.QX11Info.display()