""" Fixture configuration
"""

class Config(object):
    __slots__ = ()

    def __init__(self, **kwargs):
        [setattr(self, k, v) for (k, v) in kwargs.items()]

    def update(self, cfg):
        for k in cfg:
            if k not in self.__slots__:
                raise ValueError("Unknown config option: {0}".format(k))
            setattr(self, k, cfg[k])

