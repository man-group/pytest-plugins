"""
Custom autodoc generator, which tries to use Python's own import
machinery to see what's visible in a package, rather than walking through
the internals of the package.
"""

import os
import sys
import types


def obj_in_package(obj, package_name):
    if isinstance(obj, types.ModuleType):
        return obj.__name__.startswith(package_name)
    return hasattr(obj, '__module__') and obj.__module__ \
        and obj.__module__.startswith(package_name)


def write_autodoc_file(package_name, dirname='.'):
    __import__(package_name)
    package = sys.modules[package_name]
    subpackage_name = package_name.split('.')[-1]

    fd = open(os.path.join(dirname, package_name + '.rst'), 'w')
    fd.write(':mod:`%s` Package\n%s\n' \
                 % (subpackage_name, '=' * (len(subpackage_name) + 15)))
    write_module_autodoc(fd, package, package_name)
    fd.close()


def write_module_autodoc(fd, mod, package_name):
    fd.write('\n.. module:: %s\n' % (mod.__name__,))

    submods = []

    for name in dir(mod):
        if name.startswith('_'):
            continue

        obj = getattr(mod, name)
        if not obj_in_package(obj, package_name):
            continue

        if isinstance(obj, types.TypeType):
            fd.write('\n.. autoclass:: %s\n    :members:\n    :inherited-members:\n' % obj.__name__)
        elif isinstance(obj, types.FunctionType):
            fd.write('\n.. autofunction:: %s\n' % obj.__name__)
        elif isinstance(obj, types.ModuleType):
            submods.append(obj)

    for submod in submods:
        submod_name = submod.__name__.split('.')[-1]
        fd.write('\n:mod:`%s` Module\n%s\n' \
                     % (submod_name, '-' * (len(submod_name) + 14)))
        write_module_autodoc(fd, submod, package_name)


def generate(distribution):
    dest_dir = os.path.join(os.path.abspath('docs'), 'autodoc')
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    print "Writing files to: %s" % dest_dir
    write_autodoc_file(distribution.get_name(), dest_dir)
