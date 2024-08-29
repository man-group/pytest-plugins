
def test_q_application(q_application):
    from PyQt4 import QtGui
    assert QtGui.QX11Info.display()
