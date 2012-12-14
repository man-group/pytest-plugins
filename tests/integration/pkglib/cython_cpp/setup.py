#!/bin/env python
from pkglib.setuptools import setup
from pkglib.setuptools.extension import Extension

cfunctions = Extension("acme.foo._cppcython",
                            language="c++",
                            extra_compile_args=["-std=gnu++98"],
                            sources=["src/cppcython.pyx", "src/cppmodule.cpp"])

setup(ext_modules = [cfunctions])
