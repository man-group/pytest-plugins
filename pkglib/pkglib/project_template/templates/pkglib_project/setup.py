# $HeadURL$
try:
    from pkglib.setuptools import setup
except ImportError:
    print "PkgLib is not available. Please run \"easy_install pkglib\""
    import sys
    sys.exit(1)

# ------------------ Define your C-extensions here --------------------- #

# Conventions:
# Source code under '<package root>/src/'
# Extension modules names begin with an underscore: eg, '_xyz'
# to differentiate them from regular Python modules.

# import numpy
# extra_compile_args = ['-O0']

# setup( ext_modules = [
#        Extension('acme.mypackage._foo', ['src/foo1.c', 'src/foo2.c']  \
#                   include_dirs=[ numpy.get_include() ],
#                   extra_compile_args=extra_compile_args,
#        ),
#        Extension('acme.mypackage._bar', ['src/bar1.c', 'src/bar2.c']  \
#                   include_dirs=[ numpy.get_include() ],
#                   extra_compile_args=extra_compile_args,
#       ),
# ])

setup()
