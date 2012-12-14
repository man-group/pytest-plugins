"""
Some fairly horrendous monkey-patching methods for httplib to enable us to
get at the return codes from recent HTTP calls and re-raise bad codes as
non-zero exit codes, something that isn't currently supported in 
distutils/setuptools/distribute etc.
"""
from contextlib import contextmanager
import httplib as _httplib

@contextmanager
def patch_httplib():
    """
    Patch httplib to allow us to capture return codes from http calls.
    """
    # TODO - extend for HTTPS if needed
    status_codes = []
    class PatchedHTTPResponse(_httplib.HTTPResponse):
        def begin(self):
            _httplib.HTTPResponse.begin(self)
            status_codes.append(self.status)
    _httplib.HTTPConnection.response_class = PatchedHTTPResponse
    yield status_codes
    _httplib.HTTPConnection.response_class = _httplib.HTTPResponse
