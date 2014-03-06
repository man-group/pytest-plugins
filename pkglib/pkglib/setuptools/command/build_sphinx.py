""" Sphinx Documentation Builder
"""

import os
import sys
import types

from setuptools import Command

from pkglib.sphinx import autodoc, dynamicautodoc

from .base import CommandMixin, fetch_build_eggs

__all__ = ['build_sphinx']


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
        ('source-dir=', 's', 'Source directory'),
        ('build-dir=', None, 'Build directory'),
        ('autodoc-dynamic', None, 'Autodoc uses import, not directory walk'),
        ('autodoc-external-methods', None,
         'Autodoc includes methods defined in other packages'),
    ]
    boolean_options = ['all-files', 'doctest', 'autodoc-dynamic', 'no-build',
                       'no-doctest', 'autodoc-external-methods']

    def initialize_options(self):
        self.all_files = True
        self.doctest = True
        self.no_doctest = False
        self.no_build = False
        self.build_dir = 'build/sphinx'
        self.source_dir = 'docs'
        self.autodoc_dynamic = False
        self.autodoc_external_methods = True

    def finalize_options(self):
        # Backwards compatibility here, --doctest wasn't on by default before
        self.doctest = not self.no_doctest

    def _obj_in_package(self, obj):
        """True if an object comes from the package we're interested
        in."""
        if isinstance(obj, types.ModuleType):
            return obj.__name__.startswith(self.distribution.get_name())
        return (hasattr(obj, '__module__') and obj.__module__
                and obj.__module__.startswith(self.distribution.get_name()))

    def _skip_member(self, obj):
        """Called by Sphinx to decide if to skip a member."""
        skip = (not self._obj_in_package(obj)
                or getattr(obj, '__name__', '').startswith('_'))
        if skip:
            print('skip_member: skipping ' + str(obj))

        return skip

    def _process_docstring(self, obj, lines):
        """Called by Sphinx to preprocess a list of docstring lines
        inplace."""
        if not self._obj_in_package(obj):
            # Don't run doc-tests from other packages.
            # This is a bit of a hack, but it's no big deal if we break
            # the examples; sphinx.ext.doctest will just ignore them in
            # that case.
            lines[:] = [line + ' # doctest: +SKIP'
                        if line.strip().startswith('>>> ')
                        else line for line in lines]

    def _make_sphinx_setup(self, prev_setup):

        def skip_member(_app, _what, _name, obj, _skip, _options):
            return self._skip_member(obj)

        def process_docstring(_app, _what, _name, obj, _options, lines):
            return self._process_docstring(obj, lines)

        def setup(app):
            """Called by Sphinx to setup our app."""
            prev_setup(app)
            if self.autodoc_external_methods:
                print('build_sphinx.setup: '
                      'overriding autodoc-process-docstring.')
                app.connect('autodoc-process-docstring', process_docstring)
            else:
                print('build_sphinx.setup: overriding autodoc-skip-member.')
                app.connect('autodoc-skip-member', skip_member)

        return setup

    def run_sphinx(self, builder="html"):
        # Lazy import of sphinx config
        from pkglib.sphinx import conf

        # Override setup function. Will be called by Sphinx, via conf.py file.
        conf.setup = self._make_sphinx_setup(conf.setup)

        # Set project name in the conf package directly
        conf.project = self.distribution.metadata.get_name()

        # Setup build directories

        if not os.path.isdir(self.build_dir):
            os.makedirs(self.build_dir)

        doctree_dir = os.path.join(self.build_dir, 'doctrees')
        if not os.path.isdir(doctree_dir):
            os.makedirs(doctree_dir)

        builder_target_dir = os.path.join(self.build_dir, builder)
        if not os.path.isdir(builder_target_dir):
            os.makedirs(builder_target_dir)

        source_dir = os.path.abspath(self.source_dir)

        # Build the Sphinx runner
        from sphinx.application import Sphinx  # @UnresolvedImport late import
        conf = dict(version=self.distribution.metadata.get_version(),
                    release=self.distribution.metadata.get_version())

        app = Sphinx(srcdir=source_dir,
                     confdir=source_dir,
                     outdir=os.path.abspath(builder_target_dir),
                     doctreedir=os.path.abspath(doctree_dir),
                     buildername=builder,
                     confoverrides=conf,
                     status=sys.stdout,
                     freshenv=False)

        # Run the builder

        app.build(force_all=self.all_files)

        return app.statuscode
        #print "--------- RC: %r " % rc

    def run(self):
        # Pull down Sphinx package and dependencies if they're missing
        fetch_build_eggs(['Sphinx', 'numpydoc'], dist=self.distribution)

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
