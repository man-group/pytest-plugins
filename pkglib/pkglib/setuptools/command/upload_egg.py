from distutils.errors import DistutilsOptionError
from distutils.log import INFO

from pkg_resources import Distribution

from pkglib import manage_egg

from .base import CommandMixin
from .upload import upload


class upload_egg(upload, CommandMixin):
    """
    Uploads an existing egg-file to PyPi
    """

    command_consumes_arguments = True
    description = "Upload an existing egg-file to PyPi"

    def initialize_options(self):
        self.args = []
        upload.initialize_options(self)

    def finalize_options(self):
        if len(self.args) == 0:
            raise DistutilsOptionError("Please supply the full path of the "
                                       "egg to be uploaded as an argument")
        self.egg_files = self.args
        upload.finalize_options(self)

    def run(self):
        for egg_file in self.egg_files:
            distribution = self.distribution
            self.egg_file = egg_file
            self.announce("Reading package metadata from the egg file: %s"
                          % self.egg_file, level=INFO)
            distribution.metadata = manage_egg.get_egg_metadata(self.egg_file)
            self.dist = Distribution.from_filename(self.egg_file)
            distribution.dist_files = [("bdist_egg", self.dist.py_version,
                                        self.egg_file)]
            upload.run(self)
