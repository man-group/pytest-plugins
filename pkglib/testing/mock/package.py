"""
Minimalist mock classes to replace pkg_resources.requirement and
working_set entries
"""


class Req(object):
    def __init__(self, project_name, specs):
        self.project_name = project_name
        self.specs = specs


class Pkg(object):
    def __init__(self, name, requires, src=False, location=None):
        self.project_name = name
        self._requires = requires
        if location is None:
            if src:
                self.location = "/path/to/somewhere"
            else:
                self.location = "/path/to/an.egg"
        else:
            self.location = location

    def __repr__(self):
        return "<%s>" % self.project_name

    def requires(self):
        return self._requires
