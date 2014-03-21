import base64
import os
import socket
import sys

from setuptools.command.upload_docs import upload_docs as _upload_docs
from distutils import log
from urlparse import urlparse
from pkglib.six import binary_type
from pkglib.six.moves import http_client

from pkglib import CONFIG
from .base import CommandMixin


_IS_PYTHON3 = sys.version > '3'


def b(str_or_bytes):
    """Return bytes by either encoding the argument as ASCII or simply return
    the argument as-is."""
    if not isinstance(str_or_bytes, binary_type):
        return str_or_bytes.encode('ascii')
    else:
        return str_or_bytes


class upload_docs(_upload_docs, CommandMixin):
    """ Wrapper around upload_docs command to raise correct return codes
        to the system.
    """
    __doc__ = _upload_docs.__doc__  # @ReservedAssignment
    _ok_status_codes = [200, 301]

    def run(self):
        self._run(_upload_docs, 'upload_docs')

    def upload_file(self, filename):
        content = open(filename, 'rb').read()
        meta = self.distribution.metadata
        data = {
            ':action': 'doc_upload',
            'name': meta.get_name(),
            'content': (os.path.basename(filename), content),
        }

        username, password = self.request_credentials(self.repository)

        # set up the authentication
        credentials = username + ':' + password
        if _IS_PYTHON3:  # base64 only works with bytes in Python 3.
            encoded_creds = base64.encodebytes(credentials.encode('utf8'))  # @UndefinedVariable # NOQA
            auth = bytes("Basic ")
        else:
            encoded_creds = base64.encodestring(credentials)
            auth = "Basic "
        auth += encoded_creds.strip()

        # Build up the MIME payload for the POST data
        boundary = b('--------------GHSKFJDLGDS7543FJKLFHRE75642756743254')
        sep_boundary = b('\n--') + boundary
        end_boundary = sep_boundary + b('--')
        body = []
        for key, values in data.items():
            # handle multiple entries for the same name
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if type(value) is tuple:
                    fn = b(';filename="%s"' % value[0])
                    value = value[1]
                else:
                    fn = b("")
                body.append(sep_boundary)
                body.append(b('\nContent-Disposition: form-data; name="%s"'
                              % key))
                body.append(fn)
                body.append(b("\n\n"))
                body.append(b(value))
                if value and value[-1] == b('\r'):
                    body.append(b('\n'))  # write an extra newline (lurve Macs)
        body.append(end_boundary)
        body.append(b("\n"))
        body = b('').join(body)

        self.announce("Submitting documentation to %s" % (self.repository),
                      log.INFO)

        # build the Request
        # We can't use urllib2 since we need to send the Basic
        # auth right with the first request
        schema, netloc, url, params, query, fragments = \
            urlparse(self.repository)
        assert not params and not query and not fragments
        if schema == 'http':
            conn = http_client.HTTPConnection(netloc)
        elif schema == 'https':
            conn = http_client.HTTPSConnection(netloc)
        else:
            raise AssertionError("unsupported schema " + schema)

        data = ''
        try:
            conn.connect()
            conn.putrequest("POST", url)
            conn.putheader('Content-type',
                           'multipart/form-data; boundary=%s' % boundary)
            conn.putheader('Content-length', str(len(body)))
            conn.putheader('Authorization', auth)
            conn.endheaders()
            conn.send(body)
        except socket.error as e:
            self.announce(str(e), log.ERROR)
            return

        r = conn.getresponse()
        if r.status == 200:
            self.store_credentials(username, password)
            self.announce('Server response (%s): %s' % (r.status, r.reason),
                          log.INFO)
        elif r.status == 301:
            location = r.getheader('Location')
            if location is None:
                location = '%s/docs/%s/' % (CONFIG.pypi_url, meta.get_name())
            self.announce('Upload successful. Visit %s' % location,
                          log.INFO)
        else:
            self.announce('Upload failed (%s): %s' % (r.status, r.reason),
                          log.ERROR)
        if self.show_response:
            print("%s %s %s" % ('-' * 75, r.read(), '-' * 75))
