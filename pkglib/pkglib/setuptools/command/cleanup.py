import sys
import os
import shutil
from setuptools import Command
from pkg_resources import working_set

from distutils import log

from base import CommandMixin


class cleanup(Command, CommandMixin):
    """ Clean up the virtual environment """
    description = "Clean up the virtual environment"

    user_options = [
    ]
    boolean_options = [
    ]

    whitelist = [
         'pip',
         'distribute',
         'setuptools',
    ]
    open_files = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.open_files = self.get_open_files()

    def filter_victim(self, victim):
        basename = os.path.basename(victim)
        for i in self.whitelist:
            if basename.startswith(i):
                return False
        if not victim.endswith('.egg'):
            return False
        return True

    def filter_open_files(self, victim):
        # Check for file locks
        for pid, filename in self.open_files:
            if victim in filename:
                log.warn("Can't delete %s, locked by pid : %s" % (victim, pid))
                return False
        return True

    def find_victims(self):
        active_things = set([i.location for i in working_set if
                            i.location.startswith(sys.exec_prefix)])
        installed_things = set([i for i in self.get_site_packages().listdir()
                                if self.filter_victim(i)])
        victims = installed_things.difference(active_things)
        victims = filter(self.filter_open_files, victims)
        return sorted(victims)

    def run(self):
        for victim in self.find_victims():
            if os.path.isdir(victim):
                self.execute(shutil.rmtree, (victim,),
                             'Deleting directory {}'.format(victim))
            else:
                self.execute(os.unlink, (victim,),
                             'Deleting {}'.format(victim))
