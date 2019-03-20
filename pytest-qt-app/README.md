# Pytest QT Fixture
        
Set up a Q Application for QT with an X-Window Virtual Framebuffer (Xvfb).
        
## Installation

Install using your favourite package installer:
```bash
    pip install pytest-qt-app
```
    
Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
    pytest_plugins = ['pytest_qt_app']
```
## Configuration

The fixtures are configured using the following evironment variables:

| Setting | Description | Default
| ------- | ----------- | -------
| SERVER_FIXTURES_XVFB | Xvfb server executable | `/usr/bin/Xvfb`

## Usage

Here's a little test that shows it working:

```python
    from PyQt4 import Qtgui
    
    def test_q_application(q_application):
        # This shows the display is connected properly to the Xvfb
        assert QtGui.QX11Info.display()         
```