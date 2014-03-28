try:
    from pkglib_testing.pytest.q_application import q_application  # @UnusedImport  # NOQA
    from PyQt4 import QtGui

except ImportError:
    print "Skipping QT tests, not installed"

else:
    def test_q_application(q_application):
        assert QtGui.QX11Info.display()
