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


def requires_config(vars_):
    """ Decorator for fixtures that will skip tests if the required config variables
        are missing from the configuration
    """
    def decorator(f):
        # We need to specify 'request' in the args here to satisfy pytest's fixture logic
        @functools.wraps(f)
        def wrapper(request, *args, **kwargs):
            for var in vars_:
                if not getattr(CONFIG, var):
                    pytest.skip('config variable {} missing, skipping test'.format(var))
            return f(request, *args, **kwargs)
        return wrapper
    return decorator


def yield_requires_config(vars_):
    """ As above but for yield_fixtures
    """
    def decorator(f):
        # We need to specify 'request' in the args here to satisfy pytest's fixture logic
        @functools.wraps(f)
        def wrapper(request, *args, **kwargs):
            for var in vars_:
                if not getattr(CONFIG, var):
                    pytest.skip('config variable {} missing, skipping test'.format(var))
            gen = f(*args, **kwargs)
            yield gen.next()
        return wrapper
    return decorator
