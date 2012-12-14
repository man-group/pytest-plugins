# -*- coding: utf-8 -*-
"""
Sphinx Auto-generated documentation spider
"""
import os

INIT = '__init__.py'


def generate(distribution):
    """
    Generate package documentation tree from source code docstrings.
    Docstrings should follow this method as an example.

    Parameters
    ----------
    argument_1 : type of argument_1
        Description of argument_1
    argument_2 : type of argument_2
        Description of argument_2

    Returns
    ----------
    return_value : type of return_value
        Description of return_value

    Attributes
    ----------
    attr_1  : type of attr_1
        Description of atrr_1. This would only be used on a class definition.

    Notes
    -----
    Some Notes can go here.

    Examples
    --------
    Here is a good place to put doctest-style examples::

        def foo():
            return 'bar'
        >>> 1 + 1
        2
        >>> 2 + 2
        4

    See Also
    --------
    somemodule.func, somemodule.otherfunc
    """
    print "Auto-generating documentation from docstrings."
    dest_dir = os.path.join(os.path.abspath('docs'), 'autodoc')
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    print "Writing files to: %s" % dest_dir

    class Opts(object):
        dryrun = False
        header = 'Project'
        suffix = 'rst'
        maxdepth = 4
        force = True
        notoc = True
        destdir = dest_dir

    for ns in set([d.split('.')[0] for d in distribution.namespace_packages]):
        recurse_tree(ns, [], Opts(), [ns])

# The following parts of this script are derived from sphinx-autopackage-script,
#  which is under the GPL. Original GPL licence follows:

# Copyright 2008 Société des arts technologiques (SAT), http://www.sat.qc.ca/
# Copyright 2010 Thomas Waldmann <tw AT waldmann-edv DOT de>
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# automodule options
# Instead look at "[build_sphinx]\nautodoc-external-methods = 0" in setup.cfg.
OPTIONS = ['members',
           'undoc-members',
           'inherited-members',
           'show-inheritance',
          ]


def makename(package, module):
    """Join package and module with a dot."""
    # Both package and module can be None/empty.
    if package:
        name = package
        if module:
            name += '.' + module
    else:
        name = module
    return name


def write_file(name, text, opts):
    """Write the output file for module/package <name>."""
    if opts.dryrun:
        return
    fname = os.path.join(opts.destdir, "%s.%s" % (name, opts.suffix))
    if not opts.force and os.path.isfile(fname):
        print 'File %s already exists, skipping.' % fname
    else:
        print 'Creating file %s.' % fname
        f = open(fname, 'w')
        f.write(text)
        f.close()


def format_heading(level, text):
    """Create a heading of <level> [1, 2 or 3 supported]."""
    underlining = ['=', '-', '~', ][level - 1] * len(text)
    return '%s\n%s\n\n' % (text, underlining)


def format_directive(module, package=None):
    """Create the automodule directive and add the options."""
    directive = '.. automodule:: %s\n' % makename(package, module)
    for option in OPTIONS:
        directive += '    :%s:\n' % option
    return directive


def create_module_file(package, module, opts):
    """Build the text of the file and write the file."""
    text = format_heading(1, '%s Module' % module)
    text += format_heading(2, ':mod:`%s` Module' % module)
    text += format_directive(module, package)
    write_file(makename(package, module), text, opts)


def create_package_file(root, master_package, subroot, py_files, opts, subs, exclude_packages):
    """Build the text of the file and write the file."""
    package = os.path.split(root)[-1]
    text = format_heading(1, ':mod:`%s` Package' % package)
    # add each package's module
    for py_file in py_files:
        if shall_skip(os.path.join(root, py_file)):
            continue
        is_package = py_file == INIT
        py_file = os.path.splitext(py_file)[0]
        py_path = makename(subroot, py_file)
        if is_package:
            # Don't need this really, it's already at
            # the top of the file and creates unnecessary
            # index entries
            #heading = ':mod:`%s` Package' % package
            pass
        else:
            heading = ':mod:`%s` Module' % py_file
            text += format_heading(2, heading)
        text += format_directive(is_package and subroot or py_path, master_package)
        text += '\n'

    # build a list of directories that are packages (they contain an INIT file)
    subs = [sub for sub in subs if os.path.isfile(os.path.join(root, sub, INIT))]
    # if there are some package directories, add a TOC for theses subpackages
    if subs:
        text += format_heading(2, 'Subpackages')
        text += '.. toctree::\n\n'
        for sub in subs:
            text += '    %s.%s\n' % (makename(master_package, subroot), sub)
        text += '\n'

    name = makename(master_package, subroot)
    if not name in exclude_packages:
        write_file(makename(master_package, subroot), text, opts)


def create_modules_toc_file(master_package, modules, opts, name='modules'):
    """
    Create the module's index.
    """
    text = format_heading(1, '%s Modules' % opts.header)
    text += '.. toctree::\n'
    text += '   :maxdepth: %s\n\n' % opts.maxdepth

    modules.sort()
    prev_module = ''
    for module in modules:
        # look if the module is a subpackage and, if yes, ignore it
        if module.startswith(prev_module + '.'):
            continue
        prev_module = module
        text += '   %s\n' % module

    write_file(name, text, opts)


def shall_skip(module):
    """
    Check if we want to skip this module.
    """
    # skip it, if there is nothing (or just \n or \r\n) in the file
    name = os.path.basename(module)
    skip = (name != INIT and name.startswith('_')) or os.path.getsize(module) < 3
    if skip:
        print "Skipping %s (empty or private module)" % module
    return skip


def is_excluded(root, excludes):
    """
    Check if the directory is in the exclude list.

    Note: by having trailing slashes, we avoid common prefix issues, like
          e.g. an exlude "foo" also accidentally excluding "foobar".
    """
    sep = os.path.sep
    if not root.endswith(sep):
        root += sep
    for exclude in excludes:
        if root.startswith(exclude):
            return True
    return False


def recurse_tree(path, excludes, opts, exclude_packages=[]):
    """
    Look for every file in the directory tree and create the corresponding
    ReST files.
    """

    # use absolute path for root, as relative paths like '../../foo' cause
    # 'if "/." in root ...' to filter out *all* modules otherwise
    path = os.path.abspath(path)
    # check if the base directory is a package and get is name
    if INIT in os.listdir(path):
        package_name = path.split(os.path.sep)[-1]
    else:
        package_name = None

    toc = []
    tree = my_walk(path)
    for root, subs, files in tree:
        # keep only the Python script files
        py_files = sorted([f for f in files if os.path.splitext(f)[1] == '.py'])
        if INIT in py_files:
            py_files.remove(INIT)
            py_files.insert(0, INIT)
        # check if there are valid files to process
        # TODO: could add check for windows hidden files
        if not py_files  \
        or is_excluded(root, excludes):
            continue
        if INIT in py_files:
            # we are in package ...
            if (# ... with subpackage(s)
                subs
                or
                # ... with some module(s)
                len(py_files) > 1
                or
                # ... with a not-to-be-skipped INIT file
                not shall_skip(os.path.join(root, INIT))
               ):
                subroot = root[len(path):].lstrip(os.path.sep).replace(os.path.sep, '.')
                create_package_file(root, package_name, subroot, py_files, opts, subs, exclude_packages)
                name = makename(package_name, subroot)
                if not name in exclude_packages:

                    toc.append(name)
        elif root == path:
            # if we are at the root level, we don't require it to be a package
            for py_file in py_files:
                if not shall_skip(os.path.join(path, py_file)):
                    module = os.path.splitext(py_file)[0]
                    create_module_file(package_name, module, opts)

                    toc.append(makename(package_name, module))

    # create the module's index
    if not opts.notoc:
        create_modules_toc_file(package_name, toc, opts)


def my_walk(root):
    """Our own implementation of os.walk, as we want to skip subdirs starting with '_'."""

    names = os.listdir(root)
    subs = []
    files = []
    for name in names:
        if os.path.isdir(os.path.join(root, name)):
            subs.append(name)
        else:
            files.append(name)

    subs = sorted([sub for sub in subs if sub[0] not in ['.', '_']])

    # recurse into subdirs -- inefficient list joining, but who needs speed here?
    res = [(root, subs, files)]
    for sub in subs:
        res.extend(my_walk(os.path.join(root, sub)))

    return res
