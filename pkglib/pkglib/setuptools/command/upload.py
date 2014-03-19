import io
import os
import socket
import platform

from base64 import standard_b64encode
from hashlib import md5

from distutils.command.upload import upload as _upload
from distutils.spawn import spawn
from distutils import log

from urlparse import urlparse
from urllib2 import urlopen, Request, HTTPError

from .base import CommandMixin


class upload(_upload, CommandMixin):
    """ Wrapper around upload command to raise correct return codes
        to the system.
    """
    __doc__ = _upload.__doc__  # @ReservedAssignment
    _ok_status_codes = [200]

    def run(self):
        self._run(_upload, 'upload')

    def _create_upload_data(self, command, filename, content, pyversion, meta):
        data = {':action': 'file_upload',  # action
                'protcol_version': '1',

                # identify release
                'name': meta.get_name(),
                'version': meta.get_version(),

                # file content
                'content': (os.path.basename(filename), content),
                'filetype': command,
                'pyversion': pyversion,
                'md5_digest': md5(content).hexdigest(),

                # additional meta-data
                'metadata_version': '1.0',
                'summary': meta.get_description(),
                'home_page': meta.get_url(),
                'author': meta.get_contact(),
                'author_email': meta.get_contact_email(),
                'license': meta.get_licence(),
                'description': meta.get_long_description(),
                'keywords': meta.get_keywords(),
                'platform': meta.get_platforms(),
                'classifiers': meta.get_classifiers(),
                'download_url': meta.get_download_url(),
                # PEP 314
                'provides': meta.get_provides(),
                'requires': meta.get_requires(),
                'obsoletes': meta.get_obsoletes(),
                }
        comment = ''
        if command == 'bdist_rpm':
            dist, version, _ = platform.dist()
            if dist:
                comment = 'built for %s %s' % (dist, version)
        elif command == 'bdist_dumb':
            comment = 'built for %s' % platform.platform(terse=1)
        data['comment'] = comment

        if self.sign:
            data['gpg_signature'] = (os.path.basename(filename) + ".asc",
                                     open(filename + ".asc").read())

        return data

    def _submit_request(self, request, username, password):
        try:
            result = urlopen(request)
            status = result.getcode()
            msg = result.msg

            if self.show_response:
                resp = result.read()
                try:
                    resp = resp.decode('utf-8')
                except:
                    resp = "Error decoding result to UTF-8\n%s" % str(resp)
                msg += ': ' + '\n'.join(('-' * 75, resp, '-' * 75))
        except HTTPError as e:
            status = e.code
            msg = e.msg + ': ' + e.read().decode('utf-8')
        except socket.error as e:
            status = e.errno
            msg = str(e)

        if status == 200:
            self.store_credentials(username, password)
            self.announce('Server response (%s): %s' % (status, msg),
                          log.INFO)
        else:
            self.announce('Upload failed (%s): %s' % (status, msg),
                          log.ERROR)

    def _generate_mime_body(self, data, boundary):
        sep_boundary = b'\n--' + boundary.encode('ascii')
        end_boundary = sep_boundary + b'--'
        body = io.BytesIO()
        for key, value in data.items():
            title = '\nContent-Disposition: form-data; name="%s"' % key
            # handle multiple entries for the same name
            if not isinstance(value, list):
                value = [value]
            for value in value:
                if type(value) is tuple:
                    title += '; filename="%s"' % value[0]
                    value = value[1]
                else:
                    value = str(value).encode('utf-8')
                body.write(sep_boundary)
                body.write(title.encode('utf-8'))
                body.write(b"\n\n")
                body.write(value)
                if value and value[-1:] == b'\r':
                    body.write(b'\n')  # write an extra newline (lurve Macs)
        body.write(end_boundary)
        body.write(b"\n")
        body = body.getvalue()

        return body

    def upload_file(self, command, pyversion, filename):
        # Makes sure the repository URL is compliant
        schema, _, _, params, query, fragments = urlparse(self.repository)

        if params or query or fragments:
            raise AssertionError("Incompatible url %s" % self.repository)

        if schema not in ('http', 'https'):
            raise AssertionError("unsupported schema " + schema)

        # Sign if requested
        if self.sign:
            gpg_args = ["gpg", "--detach-sign", "-a", filename]
            if self.identity:
                gpg_args[2:2] = ["--local-user", self.identity]
            spawn(gpg_args,
                  dry_run=self.dry_run)

        # Fill in the data - send all the meta-data in case we need to
        # register a new release
        f = open(filename, 'rb')
        try:
            content = f.read()
        finally:
            f.close()

        # set up the authentication
        username, password = self.request_credentials(self.repository)

        data = self._create_upload_data(command, filename, content, pyversion,
                                        self.distribution.metadata)

        # Build up the MIME payload for the POST data
        boundary = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
        body = self._generate_mime_body(data, boundary)

        self.announce("Submitting [%s] to [%s]" % (filename, self.repository),
                      log.INFO)

        # build the Request
        # set up the authentication
        user_pass = (username + ":" + password).encode('ascii')
        # The exact encoding of the authentication string is debated.
        # Anyway PyPI only accepts ascii for both username or password.
        auth = "Basic " + standard_b64encode(user_pass).decode('ascii')

        headers = {'Content-type': ('multipart/form-data; boundary=%s' %
                                    boundary),
                   'Content-length': str(len(body)),
                   'Authorization': auth}

        # send the data
        request = Request(self.repository, data=body, headers=headers)
        self._submit_request(request, username, password)
