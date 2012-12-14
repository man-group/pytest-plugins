from pkglib.setuptools import setup
from pkglib.setuptools.extension import Extension

setup(ext_modules=[Extension('acme.foo.ext', ['src/ext.c'], include_dirs=['src'])])
