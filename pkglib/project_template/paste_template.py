import os
import re
import sys
import shutil

from paste.util.template import paste_script_template_renderer
from paste.script.templates import Template, var
from paste.script.create_distro import CreateDistroCommand

from pkglib import CONFIG
from pkglib.manage import is_inhouse_package


setattr(CreateDistroCommand, '_bad_chars_re', re.compile('[^a-zA-Z0-9_\.]'))

NAMESPACE_INIT = '''
# $HeadURL$
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
import modulefinder
for p in __path__:
    modulefinder.AddPackagePath(__name__, p)
'''

class Package(Template):
    template_renderer = staticmethod(paste_script_template_renderer)
    # Common defaults
    vars = [
        var('version', 'Version (like 1.0)', '1.0.0'),
        var('description', 'One-line description of the package', ''),
        var('author', 'Author Name', 'Your Name'),
        var('author_email', 'Author Email', os.environ['USER'] + '@' + CONFIG.email_suffix),
    ]

    def makedir(self, path):
        '''Make a director ignoring if its present already.'''
        try:
            os.mkdir(path)
        except OSError:
            pass

    def write_content(self, filename, content=''):
        '''Used to make __init__.py with or without content.'''
        with open(filename, 'wb') as f:
            f.write(content)

    def pre(self, command, output_dir, vars):
        if not is_inhouse_package(vars['package']):
            sys.exit("Error: Package name doesn't start with an company prefix.\n" \
                     "Prefixes are:\n" \
                     "%s" % '\n'.join(CONFIG.namespaces))
        prefix, package = vars['package'].split('.', 1)
        vars['package'] = package
        vars['namespace_package'] = prefix
        vars['project_nodot'] = vars['project'].replace('.', '')
        vars['project_dir'] = vars['project'].replace('.', '/')

    def post(self, command, output_dir, vars):
        # relocate to deal with unusal depth packages
        package_subpath = vars['package'].split('.')
        if len(package_subpath) > 1:
            print 'Begining directory restructure due to the package depth being greater than two.'
            project = vars['project']
            project_root = os.path.abspath(os.path.join(os.curdir, project))
            package_top = os.path.join(project_root, project.split('.')[0])
            old_code_root = os.path.join(package_top, vars['package'])
            new_code_root = package_top

            # make the required directory structure
            os.chdir(package_top)
            for dirname in package_subpath:
                self.makedir(dirname)
                # change into the just created dir to make the next level down
                os.chdir(dirname)
                # build up the path to the final location the package will be moved to
                new_code_root = os.path.join(new_code_root, dirname)
                # if this isn't the final code_root directory then add a __init__.py file
                if dirname != package_subpath[-1]:
                    print 'creating namespace __init__.py for {path}'.format(path=new_code_root)
                    self.write_content('__init__.py', NAMESPACE_INIT)

            os.chdir(package_top)
            # move the code leaf of the python package into the newly created directory tree
            print 'Relocating {old} to {new}'.format(old=old_code_root, new=new_code_root)
            for el in os.listdir(old_code_root):
                el_path = os.path.join(old_code_root, el)
                shutil.move(el_path, new_code_root)
            # remove the old code leaf
            os.rmdir(old_code_root)

        print "-" * 40
        print "Successfully created %s" % output_dir
        print "Template at: %r" % self.template_dir()


class CorePackage(Package):
    _template_dir = 'templates/pkglib_project'
    summary = "Standard pkglib-enabled project."
