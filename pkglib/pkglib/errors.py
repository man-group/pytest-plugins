"""Exceptions module."""


class UserError(Exception):
    """Error that should be reported cleanly to the user"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.msg = str(": ".join(str(a) for a in args))
        if kwargs:
            self.msg += "(%s)" % kwargs
