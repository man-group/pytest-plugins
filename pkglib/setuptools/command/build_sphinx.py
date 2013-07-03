""" Sphinx Documentation Builder
"""
import sys
import types

from setuptools import Command

from pkglib.sphinx import autodoc
from pkglib.sphinx import dynamicautodoc

from base import CommandMixin


class build_sphinx(Command, CommandMixin):
    """ Build project documnetation """
    description = "Build project documentation"
    # Cut-down set of user options for backwards compatibility
    # with old setup.cfg files.
    user_options = [
        # TODO: remove this first option, it's a no-op
        ('all-files', 'a', 'build all files'),
        ('doctest', None, 'run doctests'),
        ('no-doctest', None, 'Skip doctests'),
        ('no-build', None, 'Skip build'),
        ('no-sphinx', None, 'Skip Sphinx operations'),
        ('source-dir=', 's', 'Source directory'),
        ('build-dir=', None, 'Build directory'),
        ('autodoc-dynamic', None, 'Autodoc uses import, not directory walk'),
        ('autodoc-external-methods', None, 'Autodoc includes methods defined in other packages'),
    ]
    boolean_options = ['all-files', 'doctest', 'autodoc-dynamic', 'no-build', 'no-doctest',
                       'autodoc-external-methods', 'no-sphinx']

    def initialize_options(self):
        self.all_files = True
        self.doctest = True
        self.no_doctest = False
        self.no_build = False
        self.build_dir = 'build/sphinx'
        self.source_dir = 'docs'
        self.autodoc_dynamic = False
        self.autodoc_external_methods = True
	self.no_sphinx = False

    def finalize_options(self):
        self.doctest = not self.no_doctest  # Backwards compatibility here, --doctest wasn't on by default before
        pass

    def _make_sphinx_setup(self):
        package_name = self.distribution.get_name()

        def obj_in_package(obj):
            """True if an object comes from the package we're interested in."""
            if isinstance(obj, types.ModuleType):
                return obj.__name__.startswith(package_name)
            return hasattr(obj, '__module__') and obj.__module__ \
                and obj.__module__.startswith(package_name)

        def skip_member(app, what, name, obj, skip, options):
            """Called by Sphinx to decide if to skip a member."""
            skip = not obj_in_package(obj) or getattr(obj, '__name__', '').startswith('_')
            if skip:
                print 'skip_member: skipping', obj

            return skip

        def setup(app):
            """Called by Sphinx to setup our app."""
            print 'build_sphinx.setup called. overriding autodoc-skip-member.'
            app.connect('autodoc-skip-member', skip_member)

        return setup

    def run_sphinx(self, builder="html"):
        # Lazy import of sphinx config
        from pkglib.sphinx import conf

        if not self.autodoc_external_methods:
            # Override setup function. Will be called by Sphinx, via conf.py file.
            conf.setup = self._make_sphinx_setup()

        # Set project name in the conf package directly
        conf.project = self.distribution.metadata.get_name()

        # Setup build directories
        from path import path
        build_dir = path(self.build_dir)
        build_dir.makedirs_p()
        doctree_dir = build_dir / 'doctrees'
        doctree_dir.makedirs_p()
        builder_target_dir = build_dir / builder
        builder_target_dir.makedirs_p()

        source_dir = path(self.source_dir).abspath()

        # Build the Sphinx runner
        from sphinx.application import Sphinx
        conf = dict(version=self.distribution.metadata.get_version(),
                    release=self.distribution.metadata.get_version())

        app = Sphinx(srcdir=source_dir.abspath(), confdir=source_dir.abspath(),
                     outdir=builder_target_dir.abspath(), doctreedir=doctree_dir.abspath(),
                     buildername=builder, confoverrides=conf, status=sys.stdout, freshenv=False)

        # Run the builder

	if not self.no_sphinx:
	    app.build(force_all=self.all_files)
	    return app.statuscode
	return 0
        #print "--------- RC: %r " % rc

    def run(self):
        # Pull down Sphinx package and dependencies if they're missing
        self.fetch_build_eggs(['Sphinx', 'numpydoc'])

        if not self.no_build:
            # Generate autodocs from the source tree.
            if self.autodoc_dynamic:
                dynamicautodoc.generate(self.distribution)
            else:
                autodoc.generate(self.distribution)

            # Run Sphinx now for html
            rc = self.run_sphinx('html')
            if rc != 0:
                raise sys.exit(rc)

        # And again for doctests
        if self.doctest:
            self.distribution.have_run['sphinx'] = 0
            raise sys.exit(self.run_sphinx('doctest'))
