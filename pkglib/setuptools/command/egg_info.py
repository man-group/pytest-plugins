import os
from distutils import log

from setuptools.command.egg_info import egg_info as _egg_info
import pkg_resources

from pip.vcs import vcs

from base import CommandMixin
from pkglib.manage import (read_allrevisions_file, is_inhouse_package,
                           is_strict_dev_version)
from pkglib import CONFIG, pypi
from pkglib.setuptools import dependency


# When generating a new build tag, if one cannot be determined it will use this
DEFAULT_BUILD_TAG = ".dev1"


class egg_info(_egg_info, CommandMixin):
    """ Custom metadata functions.
    """
    user_options = [('include-test-options', None, "Include test options"),
                    ('new-build', None, "Generate a new build number"),
                    ("index-url=", "i", "base URL of Python Package Index"),
                    ] + _egg_info.user_options

    boolean_options = ['include-test-options',
                       'new-build'] + _egg_info.boolean_options

    def initialize_options(self):
        self.include_test_options = False
        self.new_build = False
        self.index_url = None
        self.pypi_client = None
        _egg_info.initialize_options(self)

    def finalize_options(self):
        from path import path
        self.index_url = self.index_url or \
                         self.maybe_add_simple_index(CONFIG.pypi_url)
        self.pypi_client = self.pypi_client or pypi.PyPi(self.index_url)

        if self.new_build:
            self.setup_new_build()

        _egg_info.finalize_options(self)

        self.egg_info = path(self.egg_info)
        self.revision_file = self.egg_info / 'revision.txt'
        self.test_option_file = self.egg_info / 'test_options.txt'
        self.all_revisions_file = self.egg_info / 'allrevisions.txt'

    def write_test_options(self):
        """ Convert raw test options into the lines to be written to
            test_options.txt
        """
        test_cmd = self.get_finalized_command('test')
        data = '\n'.join(['[test]'] + ['%s = %s' % (o[0], str(o[1])) for o in
                                          test_cmd.get_options()])
        self.write_file('test options', self.test_option_file, data)

    def write_revision(self, revno):
        """
        Used by pytagup to determine the SCM revision numbers from whence egg
        files were built.
        """
        self.write_file('revision number %s' % revno, self.revision_file,
                        str(revno))

    def read_all_revisions(self, dist):
        """Read revision from egg directory."""
        from path import path
        dist_dir = path(dist.location)
        for egg_info_dir in [dist_dir / 'EGG-INFO',
                             dist_dir / '{}.egg-info'.format(dist.project_name)]:
            all_revs_fname = egg_info_dir / 'allrevisions.txt'
            if all_revs_fname.exists():
                revisions = read_allrevisions_file(all_revs_fname)
                for rev_data in revisions:
                    if pkg_resources.safe_name(rev_data[0]) == dist.project_name:
                        return tuple(rev_data)  # name,version,url,rev
        return None

    def write_all_revisions(self):
        """ Create ``allrevisions.txt`` file containing subversion revision
            of every project upon which we depend. This won't have the
            dependencies in it if we've not yet been set-up with
            'setup.py develop' or similar.
        """
        my_dist = dependency.get_dist(self.distribution.metadata.name)

        revisions = []  # list of (name,version,url,rev) tuples

        revisions.append((self.distribution.metadata.get_name(),
                          self.distribution.metadata.get_version(),
                          self.full_url,
                          self.revision))

        # get all our requirements
        all_requires = []
        if my_dist:
            my_require = my_dist.as_requirement()
            try:
                all_requires = pkg_resources.working_set.resolve([my_require])
            except (pkg_resources.DistributionNotFound,
                    pkg_resources.VersionConflict):
                # not installed yet -- will probably be OK when we're
                # called after the build has taken place.
                pass

        for dist in all_requires:
            if dist == my_dist or not is_inhouse_package(dist.project_name):
                continue
            rev_data = self.read_all_revisions(dist)  # (name,version,url,rev)
            if rev_data:
                revisions.append(rev_data)

        data = ['# These are the VCS revision numbers used for this particular',
                '# build. This file can be used by release tools to tag a',
                '# working build.']
        for rev_data in revisions:
            data.append(','.join([str(e) for e in rev_data]))
        self.write_file("all revisions", self.all_revisions_file,
                        '\n'.join(data))

    def discover_url(self):
        location = os.path.normcase(os.path.abspath(os.curdir))
        # Pip registers the VCS handlers on import now- kinda lame really.
        import pip.vcs.subversion
        import pip.vcs.mercurial
        import pip.vcs.git
        backend = vcs.get_backend_from_location(location)
        self.revision = None

        if backend:
            bck = backend()
            url = bck.get_url(location)

            self.full_url = url

            revision = bck.get_revision(location)
            # This is similar to pip.vcs.subversion.get_src_requirement
            parts = url.split('/')
            for i in range(len(parts) - 1, 0, -1):
                if parts[i] in ('trunk', 'tags', 'tag', 'branch', 'branches'):
                    url = '/'.join(parts[:i])
                    print "discovered URL for %s backend: %s" % (backend.name, url)
                    self.distribution.metadata.url = url
                    self.revision = revision
                    break
            else:
                pass
                #print "WARNING: This is not a regular repository (no trunk, tags, or branches)"
                #print "         Using discovered URL: %s" %  self.distribution.metadata.url
        else:
            pass
            #print "WARNING: This package is not in any repository."
            #print "         Using discovered URL: %s" %  self.distribution.metadata.url

    def pin_requirements(self):
        """
        Pin all install and test requirements to their currently installed
        versions. This assumes they are already installed, so this will fail
        unless the develop stage has already been run.
        """
        ws = dict(list((i.project_name, i.version)
                       for i in pkg_resources.working_set))
        for req_set in ['install_requires', 'tests_require']:
            log.info("pinning %s" % req_set)
            old = getattr(self.distribution, req_set)
            new = []
            if old:
                for req in pkg_resources.parse_requirements(old):
                    if not req.project_name in ws:
                        raise ValueError("Requirement %s is not installed " \
                                         "(have you run python setup.py develop?)" % req.project_name)
                    new.append('%s==%s' % (req.project_name, ws[req.project_name]))
                    log.info("  %s == %s" % (req.project_name, ws[req.project_name]))
                setattr(self.distribution, req_set, new)

    def setup_new_build(self):
        """
        Sets the package version number and build tag to match the next
        development build. This will also pin all the versions of the dependencies.
        """
        version = CONFIG.dev_build_number
        tag = DEFAULT_BUILD_TAG

        latest = self.pypi_client.get_last_version(self.distribution.get_name(),
                                                   dev=True, strict=True)
        if not latest:
            log.info("No dev distributions exist yet for %s, using default version %s" % \
                     (self.distribution.get_name(), '%s%s' % (version, tag)))
        else:
            if not (is_strict_dev_version(latest)):
                raise ValueError("Latest version (%s) is not a dev build" % latest)

            build_number = latest.rsplit('dev', 1)[-1]
            tag = '.dev%d' % (int(build_number) + 1)
        log.info("created new build number: %s%s" % (version, tag))
        self.distribution.metadata.version = version
        self.tag_build = tag
        self.pin_requirements()

    def run(self):
        self.discover_url()
        _egg_info.run(self)
        if self.revision:
            self.write_revision(self.revision)
            self.write_all_revisions()
        if self.include_test_options:
            self.write_test_options()
