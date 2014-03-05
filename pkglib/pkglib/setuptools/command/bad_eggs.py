from __future__ import absolute_import, print_function

import __builtin__
import os
from urllib2 import urlopen
from contextlib import closing
from zipfile import ZipFile
from cStringIO import StringIO
from contextlib import contextmanager
from distutils import log

from setuptools.package_index import PackageIndex
from pkg_resources import parse_requirements

from pkglib.util import maybe_add_simple_index
from pkglib.setuptools import PyPIRCCommand

from upload_egg import upload_egg


class UniversalPackageIndex(PackageIndex):
    def can_add(self, dist):
        # normally this returns False if pyversion or platform are different
        return True


@contextmanager
def patch_open(files):
    __builtin__.open, orig_open = (lambda name, *args, **kwargs: StringIO(files[name]) if name in files
                                   else orig_open(name, *args, **kwargs)), __builtin__.open
    try:
        yield None
    finally:
        __builtin__.open = orig_open


def get_expected_mode(zi):
    mode = zi.external_attr >> 16
    return mode, mode | ((mode & 0o500) >> 6) * 0o111


class bad_eggs(PyPIRCCommand):
    """
    Finds eggs on PyPi that have bad permissions.
    """
    description = __doc__
    user_options = PyPIRCCommand.user_options + [
        ('fix', 'f', 'fix and upload bad eggs'),
        ]
    command_consumes_arguments = True
    fix = False
    args = []

    def run(self):
        for dist in self.scan_pypi():
            if dist.location.startswith('/'):
                continue
            if os.path.splitext(dist.location)[1] == '.egg':
                self.scan_egg(dist)
            else:
                # print dist.location
                pass

    def scan_pypi(self):
        pi = UniversalPackageIndex(maybe_add_simple_index(self.repository))
        if self.args:
            for req in parse_requirements(self.args):
                pi.find_packages(req)
                for dist in pi[req.key]:
                    if dist in req:
                        yield dist
        else:
            pi.scan_all()
            for key, urls in pi.package_pages.items():
                for url in urls:
                    pi.scan_url(url)
                for dist in pi[key]:
                    yield dist

    def scan_egg(self, dist):
        with closing(urlopen(dist.location)) as f:
            buf = f.read()
        with closing(StringIO(buf)) as fp:
            with closing(ZipFile(fp)) as z:
                broken = [(zi.filename, mode, expected) for zi, (mode, expected) in
                          ((zi, get_expected_mode(zi)) for zi in z.infolist()) if mode != expected]
        if broken:
            log.warn('Bad egg: %s', dist.location)
            for filename, mode, expected in broken:
                log.info('-- %s %o', filename, mode)
            if self.fix:
                self.fix_egg(dist, buf)

    def fix_egg(self, dist, buf):
        changes = 0
        with closing(StringIO(buf)) as fp:
            with closing(ZipFile(fp)) as z:
                with closing(StringIO()) as fixed_fp:
                    fixed_fp.write(buf[:z.infolist()[0].header_offset])
                    with closing(ZipFile(fixed_fp, 'a')) as fixed_z:
                        fixed_z.comment = z.comment
                        for zi in z.infolist():
                            mode, expected = get_expected_mode(zi)
                            zi.external_attr ^= (mode ^ expected) << 16
                            changes += 0 if mode == expected else 1
                            fixed_z.writestr(zi, z.read(zi))
                    fixed_buf = fixed_fp.getvalue()
        assert len(fixed_buf) == len(buf), 'Length changed: %d -> %d' % (len(buf), len(fixed_buf))
        assert (len(list(i for i, (c, d) in enumerate(zip(buf, fixed_buf)) if c != d)) ==
                changes), 'Wrong number of changes in zipfile buffer'
        if self.dry_run:
            egg = os.path.basename(dist.location)
            open(egg, 'wb').write(fixed_buf)
            log.info('Saved egg to %s', egg)
        else:
            self.upload_egg_buf(dist, fixed_buf)

    def upload_egg_buf(self, dist, buf):
        cmd = upload_egg(self.distribution)
        cmd.repository = self.repository
        cmd.args = [dist.location]
        cmd.ensure_finalized()
        with patch_open({dist.location: buf}):
            cmd.run()
