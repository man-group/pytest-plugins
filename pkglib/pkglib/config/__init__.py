from ..errors import UserError


class Config(object):
    """ Generic attribute bucket
    """
    def __init__(self, **kwargs):
        [setattr(self, k, v) for (k, v) in kwargs.items()]

    def update(self, cfg):
        for k in cfg:
            if k not in self.__slots__:
                raise UserError("Unknown config option: {0}".format(k))
            setattr(self, k, cfg[k])
