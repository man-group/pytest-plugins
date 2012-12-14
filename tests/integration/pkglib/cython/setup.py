from pkglib.setuptools import setup
from pkglib.setuptools.extension import Extension
setup(ext_modules=[Extension("acme.foo._mycython",
                       libraries=["m"],
                       sources=["src/mycython.pyx","src/mymodule.c"])])
