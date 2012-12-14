from setuptools.command.build_ext import build_ext as _build_ext
from distutils import log

from base import CommandMixin


# TODO: latest distribute has fixed this
class build_ext(_build_ext, CommandMixin):
    """ Custom Extension Builder. Workaround for setuptools' problems with
        building Cython.
    """
    def uses_cython(self):
        return any(s.endswith('pyx') for e in self.extensions for s in e.sources)

    def run(self):
        if self.uses_cython():
            # Cython source - use cython's build_ext
            log.info("This project uses Cython, fetching builder egg")
            self.fetch_build_eggs(['Cython'])
            from Cython.Distutils import build_ext as cython_build_ext

            # Wire it into the distribution's command registry so we can run it
            self.distribution.cmdclass['cython_build_ext'] = cython_build_ext
            self.distribution.command_obj['cython_build_ext'] = cython_build_ext(self.distribution)
            self.distribution.command_obj['cython_build_ext'].inplace = self.inplace

            # Kick off the cython build
            self.run_command('cython_build_ext')

        else:
            # Regular C Extensions, build with setuptools
            _build_ext.run(self)
