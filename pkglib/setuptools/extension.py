"""
Extension to the setuptools Extension classes.
I think I'm having an Extensisential crisis.
"""
# Here we revert to the original unpatched distutils Extension.
# This is to get around setuptools' Pyrex renaming -
# if we define .pyx files, we bloody well mean to build them
# thankyou very much!

import sys
from setuptools.extension import _Extension as Extension
import distutils.core
import distutils.extension

distutils.core.Extension = Extension
distutils.extension.Extension = Extension
if 'distutils.command.build_ext' in sys.modules:
    sys.modules['distutils.command.build_ext'].Extension = Extension


class NumpyExtension(Extension):
    """
    Mechanism allow extensions to link against numpy without
    requiring it to be installed before running setup.py.

    Numpy will need to be in setup_requires.

    eg: *setup.cfg*::

        [metadata]
        name = acme.foo
        setup_requires = numpy==1.6.0
        install_requires = numpy==1.6.0

    eg: *setup.py*::

        setup(ext_modules = [
            NumpyExtension(
            'acme.foo',
            sources=['src/foo.c', 'src/bar.c', 'src/baz.c'],
            ),
        ])


    This recipe is attributed to these lovely people here:
    http://mail.python.org/pipermail/distutils-sig/2007-September/008253.html
    """
    def __init__(self, *args, **kwargs):
        Extension.__init__(self, *args, **kwargs)

        self._include_dirs = self.include_dirs
        del self.include_dirs  # restore overwritten property

    # warning: Extension is a classic class so it's not really read-only
    @property
    def include_dirs(self):
        from numpy import get_include
        return self._include_dirs + [get_include()]
