import os

__location__ = os.path.realpath(os.path.join(os.path.dirname(__file__)))
__resource_dir__ = os.path.join(__location__, "resources")


def get_resource(resource_name):
    return os.path.join(__resource_dir__, resource_name)
