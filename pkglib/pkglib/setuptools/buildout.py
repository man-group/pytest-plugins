""" ZC.Buildout helper module.
"""
import os
import sys
import errno
import shutil
import stat
import operator
import zipimport
import copy
from distutils import log
from distutils.errors import DistutilsOptionError
from itertools import chain

import pkg_resources
from zc.buildout import easy_install
from pip.util import is_local
from setuptools.command.easy_install import chmod, uncache_zipdir

from pkglib import egg_cache, pyenv, cmdline, util
from pkglib.setuptools import dependency, graph
from pkglib.setuptools.dist import egg_distribution

############ TODO: #################################################
#  Refactor this whole module so to remove the depencency on
#  zc.buildout. We have done enough work now to customise
#  the install behavior so that we don't really need it anymore,
#  and we're having to put in hacks to make it work like distribute.
#  The 'install' method below could be moved to an override of the
#  WorkingSet.resolve method.
#
####################################################################


class EggCacheAwareAllowHostsPackageIndex(easy_install.AllowHostsPackageIndex):
    """Enhances AllowHostsPackageIndex to make it use the egg_cache"""
    def _attempt_download(self, url, filename):
        res = egg_cache.egg_cache_path_from_url(url, filename)
        if res is None:
            res = super(EggCacheAwareAllowHostsPackageIndex,
                        self)._attempt_download(url, filename)
        return res


# Monkey-patch the PackageIndex so that it uses the egg-cache
easy_install.AllowHostsPackageIndex = EggCacheAwareAllowHostsPackageIndex


class Installer(easy_install.Installer):
    """  Override some functionality of the buildout installer,
         particularly the way it always chooses develop eggs over
         all other dist choices.
    """

    def _get_dist(self, requirement, ws, always_unzip):
        """The only difference between this and the standard implementation is that it doesn't copy
        eggs from the egg cache but links to them in place."""

        __doing__ = 'Getting distribution for %r.', str(requirement)

        # Maybe an existing dist is already the best dist that satisfies the
        # requirement
        dist, avail = self._satisfied(requirement)

        if dist is None:
            if self._dest is not None:
                easy_install.logger.info(*__doing__)

            # Retrieve the dist:
            if avail is None:
                raise easy_install.MissingDistribution(requirement, ws)

            # We may overwrite distributions, so clear importer
            # cache.
            sys.path_importer_cache.clear()

            tmp = self._download_cache
            if tmp is None:
                tmp = easy_install.tempfile.mkdtemp('get_dist')

            try:
                dist = self._fetch(avail, tmp, self._download_cache)

                if dist is None:
                    raise easy_install.zc.buildout.UserError(
                        "Couldn't download distribution %s." % avail)

                if dist.precedence == pkg_resources.EGG_DIST:
                    # It's already an egg, just fetch it into the dest

                    newloc = os.path.join(
                        self._dest, os.path.basename(dist.location))

                    # The next 2 lines are new, this is the only bit that is different from the standard
                    if egg_cache.is_from_egg_cache(dist.location):
                        newloc = dist.location
                    elif os.path.isdir(dist.location):
                        # we got a directory. It must have been
                        # obtained locally.  Just copy it.
                        shutil.copytree(dist.location, newloc)
                    else:

                        if self._always_unzip:
                            should_unzip = True
                        else:
                            metadata = pkg_resources.EggMetadata(
                                zipimport.zipimporter(dist.location)
                                )
                            should_unzip = (
                                metadata.has_metadata('not-zip-safe')
                                or
                                not metadata.has_metadata('zip-safe')
                                )

                        if should_unzip:
                            easy_install.setuptools.archive_util.unpack_archive(
                                dist.location, newloc)
                        else:
                            shutil.copyfile(dist.location, newloc)

                    easy_install.redo_pyc(newloc)

                    # Getting the dist from the environment causes the
                    # distribution meta data to be read.  Cloning isn't
                    # good enough.
                    dists = pkg_resources.Environment(
                        [newloc],
                        python=easy_install._get_version(self._executable),
                        )[dist.project_name]
                else:
                    # It's some other kind of dist.  We'll let easy_install
                    # deal with it:
                    dists = self._call_easy_install(
                        dist.location, ws, self._dest, dist)
                    for dist in dists:
                        easy_install.redo_pyc(dist.location)

            finally:
                if tmp != self._download_cache:
                    shutil.rmtree(tmp)

            self._env.scan([self._dest])
            dist = self._env.best_match(requirement, ws)
            easy_install.logger.info("Got %s.", dist)

        else:
            dists = [dist]

        for dist in dists:
            if (dist.has_metadata('dependency_links.txt')
                and not self._install_from_cache
                and self._use_dependency_links
                ):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    link = link.strip()
                    if link not in self._links:
                        easy_install.logger.debug('Adding find link %r from %s', link, dist)
                        self._links.append(link)
                        self._index = easy_install._get_index(self._executable,
                                                 self._index_url, self._links,
                                                 self._allow_hosts, self._path)

        for dist in dists:
            # Check whether we picked a version and, if we did, report it:
            if not (
                dist.precedence == pkg_resources.DEVELOP_DIST
                or
                (len(requirement.specs) == 1
                 and
                 requirement.specs[0][0] == '==')
                ):
                easy_install.logger.debug('Picked: %s = %s',
                             dist.project_name, dist.version)
                if not self._allow_picked_versions:
                    raise easy_install.zc.buildout.UserError(
                        'Picked: %s = %s' % (dist.project_name, dist.version)
                        )

        return dists

    def _satisfied(self, req, source=None):
        """  Modified version of the buildout version. Changes:
             - Always choose develop eggs if we find them in site_packages.
             - Prefer dev versions of eggs from the package server over final
               version in environment (esp from CONFIG.installer_search_path)
        """
        egg_dists = [dist for dist in self._egg_dists if dist in req]
        if egg_dists:
            pkg_resources._sort_dists(egg_dists)
            log.debug(' --- we have an egg dist: %s', egg_dists)
            return egg_dists[0], None

        dists = [dist for dist in self._env[req.project_name] if
                 (dist in req and
                  (dist.location not in self._site_packages or
                   self.allow_site_package_egg(dist.project_name)))]
        if not dists:
            log.debug(' --- we have no distributions for %s that satisfies %r.',
                      req.project_name, str(req))
            return None, self._obtain(req, source)

        # Look for develop eggs - we always use these if we find them so that
        # source checkouts are 'sacrosanct'
        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST):
                log.debug(' --- we have a develop egg: %s', dist)
                return dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            log.debug(' --- we have the distribution that satisfies %r.',
                      str(req))
            return dists[0], None

        # Filter the eggs found in the environment for final/dev
        version_comparator = self.get_version_comparator(req)
        preferred_dists = [dist for dist in dists
                           if version_comparator(dist.parsed_version)]

        if preferred_dists:
            # There are preferred dists, so only use those
            dists = preferred_dists

        if not self._newest:
            # We don't need the newest, so we'll use the newest one we
            # find, which is the first returned by
            # Environment.__getitem__.
            return dists[0], None

        best_we_have = dists[0]  # Because dists are sorted from best to worst

        # We have some installed distros.  There might, theoretically, be
        # newer ones.  Let's find out which ones are available and see if
        # any are newer.  We only do this if we're willing to install
        # something, which is only true if dest is not None:

        if self._dest is not None:
            best_available = self._obtain(req, source)
        else:
            best_available = None

        if best_available is None:
            # That's a bit odd.  There aren't any distros available.
            # We should use the best one we have that meets the requirement.
            log.debug(
                '--- there are no distros available that meet %r.\n'
                '--- using our best, %s.',
                str(req), best_available)
            return best_we_have, None

        # Check we've not just picked the same distro
        if best_we_have == best_available:
            log.debug(" --- chose dist from environment: {0}".format(best_we_have))
            return best_we_have, None

        # Now pick between the version from the index server and the version
        # found in our environment. We put the environment one first here
        # so that if they're the same version, it will pick that one and we're
        # not downloading things unnecessarily
        best = self.choose_between(best_we_have, best_available,
                                   version_comparator)
        if best == best_available:
            log.debug(" --- chose dist from index server: {0}".format(best))
            return None, best

        log.debug(" --- chose dist from environment: {0}".format(best_we_have))
        return best_we_have, None

    def choose_between(self, d1, d2, comparator):
        """ Choose between two different dists, given a dev/final comparator.
            If both d1 and d2 have the same version, it will return d1.
        """
        d1_preferred = comparator(d1.parsed_version)
        d2_preferred = comparator(d2.parsed_version)
        key = operator.attrgetter('parsed_version')

        log.debug(" --- choosing between versions {0} and {1}"
                  .format(d1.version, d2.version))

        if (d1_preferred == d2_preferred):
            # I think this might be redundant as max() is order-dependent,
            # but it's nice to be explicit
            if d1.parsed_version == d2.parsed_version:
                return d1
            return max((d1, d2), key=key)
        else:
            return d1 if d1_preferred else d2

    def _maybe_add_setuptools(self, ws, dist):
        """ Here we do nothing - all our packages require
            setuptools and this comes via pkglib and friends.
            Blanking this out will suppress a bunch of spurious warnings.
        """
        pass

    def install(self, specs, working_set=None, use_existing=False,
                draw_graph=False, force_upgrade=False, reinstall=False):
        """ We've overridden the install function here to make the following
            changes:

            1) Add the ability to prefer already-installed packages over
               newer packages from the server, if the requirement is already
               satisfied (use_existing flag) dependency
            2) fix behavior wrt dependency resolution. The original version
               does not handle this case:
               A   B        Where A and B depend on C, A doesnt care
               \* /==2      which version of C it is and B is pinned to
                C           a specific version.

            In the original if there is a later version of C available it will
            pick that first and then conflict with B's pinned requirement.
            In our version we attempt to override the version picked by A, and
            replace it with the pinned version in B as it is a more specific
            requirement - ie, order-by-specivicity.

        """
        reqs = [self._constrain
                (spec if isinstance(spec, pkg_resources.Requirement)
                 else pkg_resources.Requirement.parse(spec)) for spec in specs]
        log.debug('Installing requirements: %s', repr(reqs)[1:-1])

        resolver = Resolver(self, working_set=working_set,
                            use_existing=use_existing, draw_graph=draw_graph,
                            force_upgrade=force_upgrade)
        resolver.resolve_reqs(reqs)

        new_dists = list(resolver.new_dists)
        if reinstall:
            reinstalls = [resolver.ws.find(req) for req in reqs
                          if resolver.new_dists.find(req) is None]
            log.debug('Resolved [%d] new requirements, [%d] reinstalls' %
                      (len(new_dists), len(reinstalls)))
            return new_dists + reinstalls
        else:
            log.debug('Resolved [%d] new requirements' % len(new_dists))
            return new_dists

    def get_version_comparator(self, requirement):
        """ Here we pick between 'dev' or 'final' versions.
            We want to use different logic depending on if this is a
            third-party or in-house package:
              In-house-packages: we usually want the latest dev version as
                                 keeping on head revisions is sensible to stop
                                 code going stale
              Third-party: we usually want the latest final version to protect
                           ourselves from OSS developers exposing their
                           latest untested code to the internet at large.
            To override this logic the packager needs to specify an explicit
            version pin in install_requires or similar for third-party
            packages, or use the prefer-final setup flag for in-house packages.
        """
        if util.is_inhouse_package(requirement.project_name):
            if self._prefer_final:
                log.debug(' --- in-house package, prefer-final')
                return easy_install._final_version
            else:
                log.debug(' --- in-house package, prefer-dev')
                return self.is_dev_version
        else:
            log.debug(' --- third-party package, always prefer-final')
            return easy_install._final_version

    def is_dev_version(self, parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in easy_install._final_parts):
                return True
        return False

    def _obtain(self, requirement, source=None):
        """ Copy in and override the installer's obtain method to modify the
            following behavior:
             - allow us to differentiate between third-party and in-house
               packages when applying the prefer-final / prefer-dev logic
        """
        # Look at zc.buildout source for comments on this logic
        index = self._index
        if index.obtain(requirement) is None:
            return None
        dists = [dist for dist in index[requirement.project_name] if
                 (dist in requirement and
                  (dist.location not in self._site_packages or
                   self.allow_site_package_egg(dist.project_name)) and
                  ((not source) or
                   (dist.precedence == pkg_resources.SOURCE_DIST)))]

        # Filter for final/dev and use the result if it is non empty.
        version_comparator = self.get_version_comparator(requirement)

        def parsed_version_for(dist):
            """ Sidestep some broken-ness in pkg_resource.Distribution.parsed_version
                fighting with __getattr__
            """
            return pkg_resources.parse_version(dist.version)

        filtered_dists = [dist for dist in dists
                          if version_comparator(parsed_version_for(dist))]
        if filtered_dists:
            log.debug(' --- filtered to:')
            [log.debug(' ---- {0!r}'.format(i)) for i in filtered_dists]
            dists = filtered_dists

        # The rest of this logic is as-is from buildout
        best = []
        bestv = ()
        for dist in dists:
            distv = dist.parsed_version
            if distv > bestv:
                best = [dist]
                bestv = distv
            elif distv == bestv:
                best.append(dist)

        log.debug(' --- best picks are:')
        [log.debug(' ---- {0!r}'.format(i)) for i in best]

        if not best:
            return None
        if len(best) == 1:
            return best[0]

        # TODO: buildout behavior we're not using?
        if self._download_cache:
            for dist in best:
                if easy_install.realpath(os.path.dirname(dist.location)
                                         ) == self._download_cache:
                    return dist
        best.sort()
        dist = best[-1]
        log.debug(' --- best is {0!r}'.format(dist))
        return dist


class VersionConflict(easy_install.VersionConflict):
    """ Make the version conflict errors print a trace of where they
        originated from
    """
    def __init__(self, err, ws, prev_req, best, req_graph):
        super(VersionConflict, self).__init__(err, ws)
        self.prev_req, self.best, self.req_graph = prev_req, best, req_graph

    def __str__(self):
        existing_dist, req = self.err.args

        def ancestors(req, seen=None, level=0):
            if seen is None:
                seen = set()
            yield level, req, (self.best[req.key][0] if req.key in self.best
                               else None)
            if req not in seen:
                seen.add(req)
                for r in self.req_graph.predecessors(req):
                    for t in ancestors(r, seen, level + 1):
                        yield t
        return '\n'.join(chain(("There is a version conflict.",
                                "We already have: %s" % existing_dist,),
                               () if self.prev_req is None else
                               ('  ' * l + "required by %s (%s)" % (r, d)
                                for l, r, d in ancestors(self.prev_req)),
                               ("which is incompatible with %s" % req,),
                               ('  ' * l + "required by %s (%s)" % (r, d)
                                for l, r, d in ancestors(req) if l)))


class Resolver(object):

    def __init__(self, installer, working_set=None, use_existing=False,
                 draw_graph=False, force_upgrade=False):
        self.installer = installer
        self.use_existing = use_existing
        self.draw_graph = draw_graph
        self.force_upgrade = force_upgrade

        # This is a set of processed requirements.
        self.processed = {}

        # This is the list of stuff we've installed, to hand off to the
        # post-install steps like egg-link etc
        self.new_dists = pkg_resources.WorkingSet([])

        path = installer._path
        destination = installer._dest
        if destination is not None and destination not in path:
            path.insert(0, destination)

        # Make a copy, we don't want to mess up the global w/s if this is
        # what's been passed in.

        # We can't just say WorkingSet(working_set.entries), since ws may
        # contain more paths than distributions (d'oh moment)
        self.ws = pkg_resources.WorkingSet([] if working_set is None else
                                           [d.location for d in working_set])

        # First we need to get a map of requirements for what is currently
        # installed. This is so we can play them off against new requirements.

        # For simplicity's sake, we merge all requirements matching installed
        # packages into a single requirement. This also mimics how the
        # packages would have been installed in the first place.

        self.req_graph, self.best = dependency.get_graph_from_ws(self.ws)

        log.debug("Baseline working set: (merged req, dist)")
        for dist, req in self.best.values():
            log.debug("   %25s: %r" % (req, dist))

        if draw_graph:
            graph.draw_networkx_with_pydot(self.req_graph, True)

        # This is our 'baseline' set of packages. Anything we've picked that
        # isn't in here, hasn't yet been fully installed.
        self.env = pkg_resources.Environment([] if force_upgrade
                                             or working_set is None
                                             else copy.copy(working_set.entries))

    def _get_dist(self, req):
        redo_pyc = easy_install.redo_pyc
        easy_install.redo_pyc = lambda egg: None
        try:
            return self.installer._get_dist(req, self.ws,
                                            self.installer._always_unzip)[-1]
        finally:
            easy_install.redo_pyc = redo_pyc

    def resolve_reqs(self, reqs):
        # Set up the stack, so we're popping from the front
        self.requirements = list(reversed(reqs))
        # TODO: Hmm - is this safe, as opposed to adding them to the graph
        #       as we go along (which is how it worked before) ?
        for req in self.requirements:
            self.req_graph.add_node(req)
        self.process_requirements()

    def purge_req(self, req):
        """ Purge a requirement from all our indexes, used for backtracking"""
        log.debug(' -- purging %s', req)
        self.best.pop(req.key, None)
        self.processed.pop(req, None)
        for w in self.ws, self.new_dists:
            if req.key in w.by_key:
                dependency.remove_from_ws(w, w.by_key[req.key])

    def process_requirements(self):
        while self.requirements:

            # Process dependencies breadth-first.
            req = self.installer._constrain(self.requirements.pop(0))

            if req in self.processed:
                # Ignore cyclic or redundant dependencies.
                continue

            log.debug(' - processing %r' % req)
            for r in self.req_graph.predecessors(req):
                log.debug(' -- downstream: %r' % r)

            dist, prev_req, new_req = self.resolve_requirement(req)

            if dist is not None:
                req._chosen_dist = dist
                if new_req is None and prev_req is not None:
                    prev_req._chosen_dist = dist
                    self.add_resolved_requirement(prev_req, dist)
                else:
                    self.add_resolved_requirement(req, dist)

            # HACK: using not (==) because != is broken
            if not (req == new_req):
                self.processed[req] = True

            if new_req is not None:
                self.requirements.insert(0, new_req)
                self.req_graph.add_node(new_req)
                self.req_graph.add_edge(req, new_req)
                self.req_graph.add_edge(prev_req, new_req)

            log.debug(' - finished processing %s' % req)

    def resolve_requirement(self, req):
        best = self.best.get(req.key, None)
        log.debug(" -- previous best is %r " % (best,))
        if best is not None:
            dist, prev_req = best

            # FIXME: In theory, if the previously found requirement, and the requirement
            #        we are processing are the same, we should be able to skip the
            #        checks for merging requirements process them as normal.
            #        In practice, merging a requirement with itself takes you down
            #        a differnet resolution route as it picks up stuff from the environment
            #        that we otherwise wouldn't have seen.  Leaving this as-is for now
            #        until the egg-cache changes are in.

            # if prev_req.hashCmp == req.hashCmp:
            #    log.debug(" -- already seen {0}".format(req))
            # else:

            dist, new_req = self.check_previous_requirement(req, dist, prev_req)
            return dist, prev_req, new_req

        # Find the best distribution and add it to the map.
        dist = self.ws.by_key.get(req.key)
        if dist is not None:
            log.debug(' -- dist in working set: %r' % dist)
            # We get here when the dist was already installed.
            return dist, None, None

        try:
            dist = self.env.best_match(req, self.ws)
        except pkg_resources.VersionConflict as err:
            raise VersionConflict(err, self.ws, None, self.best, self.req_graph)
        log.debug(" -- env best match is %r " % (dist))
        if (dist is not None and
            not (dist.location in self.installer._site_packages and
                 not self.installer.allow_site_package_egg(dist.project_name))):
            # We get here when things are in the egg cache, or
            # deactivated in site-packages. Need to add to
            # the working set or they don't get setup properly.
            log.debug(' -- dist in environ: %r' % dist)
            return dist, None, None

        # If we didn't find a distribution in the environment, or what we found
        # is from site-packages and not allowed to be there, try again.
        log.debug(' -- %s required %r',
                  'getting' if self.installer._dest else 'adding', str(req))
        easy_install._log_requirement(self.ws, req)
        return self._get_dist(req), None, None

    def check_previous_requirement(self, req, dist, prev_req):
        log.debug(" -- checking previously found requirements: %s vs %s",
                  prev_req, req)
        # Here is where we can possibly backtrack in our graph walking.

        # We need to check if we can merge the new requirement with ones
        # that we found previously. This merging is done on the rules of
        # specificity - ie, creating a new requirement that is bounded
        # by the most specific specs from both old and new.
        try:
            merged_req = dependency.merge_requirements(prev_req, req)
        except dependency.CannotMergeError:
            log.debug(" --- cannot merge requirements")
            raise VersionConflict(pkg_resources.VersionConflict(dist, req),
                                  self.ws, prev_req, self.best, self.req_graph)
        log.debug(" --- merged requirement: %s" % merged_req)

        if dist is None:
            log.debug(' --- purging unsatisfied requirement %s' % prev_req)
            self.purge_req(prev_req)
            return None, merged_req

        log.debug(' --- already have dist: %r' % dist)
        if not self.use_existing and all(op != '=='
                                         for op, _ in merged_req.specs):
            avail = next((dist
                          for dist in self.installer._satisfied(merged_req)
                          if dist is not None), None)
            if avail is not None and avail != dist:
                # There is a better version available; use it.
                log.debug(' --- upgrading %r to %r' % (dist, avail))
                self.backout_requirement(prev_req)
                dist = self._get_dist(merged_req)

        if prev_req.hashCmp in (req.hashCmp, merged_req.hashCmp):
            # The req is the same as one we know about; probably it was in the
            # original working set.
            log.debug(" --- prev req {0} was more specific, ignoring {1}"
                      .format(prev_req, req))
            return dist, None

        if dist in merged_req:
            # The dist we've already picked matches the more new req
            log.debug(" --- upgrading to more specific requirement %s -> %s",
                      prev_req, merged_req)

            # Add a new node in our graph for the merged requirement.
            self.req_graph.add_node(merged_req)
            for i in self.req_graph.successors(prev_req):
                log.debug(" ---- adding edge from %s to %s" % (merged_req, i))
                self.req_graph.add_edge(merged_req, i)
            return dist, merged_req

        # The dist doesn't match, back it out and send the merged req back for
        # another pass.
        log.debug(" *** overriding requirement %r with %r" % (prev_req, req))
        self.backout_requirement(prev_req)
        return None, merged_req

    def backout_requirement(self, prev_req):
        """ Back-out a requirement that's been selected as victim for back-tracking.
            We do this so that there's no chance of conflicts with the new req
            we're about to install
        """
        import networkx
        # Now we need to purge the old package and everything it brought in,

        log.debug(" *** resolving possible backtrack targets")

        prev_req_children = [i.key for i in prev_req._chosen_dist.requires()]
        backtrack_targets, shadowed_targets = dependency.get_backtrack_targets(self.req_graph, prev_req)

        for target in backtrack_targets:
            target_dist = target._chosen_dist

            if (target_dist in self.ws or target_dist in self.new_dists):
                # log.debug("**** pulling out backtrack target dist: %s" % target_dist)
                self.purge_req(target)

        # Now we need to re-map our requirements graph so that there's no
        # requirements left lying around pointing to specific versions that we
        # want to override.
        remapping = {}
        for target in shadowed_targets:
            dist, prev_req = self.best[target.key]
            if dist is not None and prev_req.key in prev_req_children:
                log.debug(' --- clearing previous link to %s', dist)
                # Create a new 'blank' requirement
                new_req = pkg_resources.Requirement.parse(prev_req.key)
                new_req._chosen_dist = prev_req._chosen_dist
                self.best[target.key] = dist, new_req
                if not (new_req == prev_req):
                    remapping[prev_req] = new_req

        # Re-labe the nodes in-place in our DiGraph. Needs networkx>=1.7
        networkx.relabel_nodes(self.req_graph, remapping, False)

    def add_resolved_requirement(self, req, dist):
        assert dist in req, ('add_resolved_requirement(): '
                             'dist "%s" not in req %s' % (dist, req))

        # If we get to this point, we're happy with this requirement and the
        # distribution that has been found for it. Store a reference to this
        # mapping, so we can get back to it if we need to backtrack.
        log.debug(" -- best is now (%s): %r" % (req, dist))
        self.best[req.key] = (dist, req)

        if dist in self.ws:
            log.debug(' -- dist in ws: %s', dist)
        else:
            if dist.location in self.installer._site_packages:
                log.debug(' -- egg from site-packages: %s', dist)
            if dist.key in self.ws.by_key:
                old_dist = self.ws.by_key[dist.key]
                log.debug(' -- removing old dist from working set: %r', old_dist)
                self.ws.entries.remove(old_dist.location)
                del self.ws.by_key[old_dist.key]
                del self.ws.entry_keys[old_dist.location]
            log.debug(' -- adding dist to target installs: %r', dist)
            self.ws.add(dist)
            self.new_dists.add(dist)

        for new_req in dist.requires(req.extras)[::-1]:
            new_req = self.installer._constrain(new_req)
            if not (new_req in self.processed or new_req in self.requirements):
                log.debug(' --- new requirement: %s' % new_req)
                self.requirements.append(new_req)

                # Add the new requirements into the graph
                self.req_graph.add_node(new_req)

                # And an edge for the new req
                self.req_graph.add_edge(req, new_req)


def uninstall_eggs(reqs):
    """ Remove eggs matching the given requirements.
    """
    # XXX This doesn't do dependencies?
    dists = []
    for i in pkg_resources.parse_requirements(reqs):
        dist = next((d for d in pkg_resources.working_set
                     if d.project_name == i.project_name), None)
        if not dist:
            raise DistutilsOptionError('Cannot remove package, not installed',
                                       i.project_name)
        if not dist.location.endswith('.egg'):
            raise DistutilsOptionError('Not an egg at %s, chickening out' %
                                       dist.location)
        dists.append(dist)

    for dist in dists:
        if is_local(dist.location):
            log.info("Removing %s (%s)" % (dist, dist.location))
            # Clear references to egg - http://trac.edgewall.org/ticket/7014
            uncache_zipdir(dist.location)
            try:
                os.remove(dist.location)
            except OSError as ex:
                if ex.errno == errno.EISDIR:
                    shutil.rmtree(dist.location)
                else:
                    raise
        else:
            log.info("Not uninstalling egg, it's not in our virtualenv: %s",
                     dist.location)
        dependency.remove_from_ws(pkg_resources.working_set, dist)


def install(cmd, reqs, add_to_global=False, prefer_final=True,
            force_upgrade=False, use_existing=False, eggs=None,
            reinstall=False):
    """ Installs a given requirement using buildout's modified easy_install.

        Parameters
        ----------
        cmd : `setuptools.Command`
           active setuptools Command class
        reqs : `list` of `str`
           list of distutils requirements, eg ['foo==1.2']
        eggs : `list` of `str`
           paths to egg files to use to satisfy requirements
        add_to_global : `bool`
           adds installed distribution to the global working_set.
           This has the effect of making them available for import within this
           process, used by fetch_build_eggs.
        prefer_final : `bool`
           Will prefer released versions of the requirements over dev versions,
           unless the package is third-party where it always prefers final
           versions.
        force_upgrade : `bool`
           Will force downloads of requirements from PyPI. This is the rough
           equivalent of ``easy_install -U acme.foo``
        use_existing : `bool`
           Will not update any packages found in the current working set
        reinstall : `bool`
            Will reinstall packages that are already installed.

        Returns
        -------
        ws : `pkg_resources.WorkingSet`
            Working Set for the distributions that were just installed.
    """
    # Remove anything we're upgrading
    if force_upgrade:
        uninstall_eggs(reqs)

    # Create installer class configured to install into wherever the command
    # class was setup for
    installer = Installer(dest=cmd.install_dir, index=cmd.index_url,
                          prefer_final=prefer_final)

    egg_dists = [egg_distribution(egg) for egg in (eggs or [])]
    installer._egg_dists = egg_dists

    # This is a bit nasty - we have to monkey-patch the filter for final
    # versions so that we can also filter for dev versions as well.

    # Set prefer_final to True, always, so it enables the filter
    easy_install.prefer_final(True)

    # This returns a WorkingSet of the packages we just installed.
    # NOTE here we pass in the existing stuff - this will prefer installed
    #      packages over ones on the server, eg an installed release
    #      version won't get trumped by a dev version on the server
    ws = pkg_resources.WorkingSet(pkg_resources.working_set.entries)

    # We must remove the package we're installing from the 'baseline' ws.
    # This way we won't get any weird requirement conflicts with new
    # versions of the package we're trying to set up
    if cmd.distribution.metadata.name:
        dist = dependency.get_dist(cmd.distribution.metadata.name)
        if dist:
            dependency.remove_from_ws(ws, dist)

    # There's a chance that there were packages in setup_requires that were
    # also in install_requires. All packages that were not in the original
    # environment and were installed during the `setup_requires` resolution
    # process are tracked by `fetched_setup_requires` field of
    # `pkglib.setuptools.dist.Distribution`.

    # Here we ensure that they're re-added for setup along with any of their
    # own dependencies if they are also part of the package install_requires.

    for d in getattr(cmd.distribution, "fetched_setup_requires", []):
        dependency.remove_from_ws(ws, d)

    # Now run the installer
    to_setup = installer.install(reqs, working_set=ws,
                                 use_existing=use_existing,
                                 force_upgrade=force_upgrade,
                                 reinstall=reinstall)

    return setup_dists(cmd, ws, to_setup, egg_dists,
                       add_to_global=add_to_global)


def setup_dists(cmd, ws, to_setup, egg_dists, add_to_global=False):
    if to_setup:
        log.debug("Packages to set-up:\n" +
                  "\n".join(' %r' % d for d in to_setup))
        downgrades = [(dist, ws.by_key[dist.key]) for dist in to_setup if
                      dist.key in ws.by_key and
                      dist.parsed_version < ws.by_key[dist.key].parsed_version]
        for dist, installed in downgrades:
            # TODO: optionally make downgrading an error
            log.warn('Downgrading %s from %s to %s',
                     dist.key, installed.version, dist.version)

        # Now we selectively run setuptool's post-install steps.
        # Luckily, the buildout installer didn't strip off any of the useful
        # metadata about the console scripts.
        return [_setup_dist(cmd, dist, install_needed=dist in egg_dists,
                            add_to_global=add_to_global) for dist in to_setup]
    else:
        log.debug('Nothing to set-up.')
        return []


def _setup_dist(cmd, dist, install_needed=False, add_to_global=False):
    if install_needed:
        with cmdline.TempDir() as tmpdir:
            dist = cmd.install_egg(dist.location, tmpdir)

    if dist.location.startswith(pyenv.get_site_packages()):
        fix_permissions(dist)

    cmd.process_distribution(None, dist, deps=False)

    # Add the distributions to the global registry if we asked for it.
    # This makes the distro importable, and classed as 'already
    # installed' by the dependency resolution algorithm.
    if add_to_global:
        dependency.remove_from_ws(pkg_resources.working_set, dist)
        pkg_resources.working_set.add(dist)

    return dist


def fix_permissions(dist):
    """ Buildout doesn't fix the package permissions like easy_install, here
        we replicate distributes's method at easy_install.unpack_and_compile
    """
    for root, _, files in os.walk(dist.location):
        for f in [os.path.join(root, i) for i in files]:
            if f.endswith('.py') or f.endswith('.dll') or \
               f.endswith('.so') and not 'EGG-INFO' in f:
                mode = ((os.stat(f)[stat.ST_MODE]) | 0o555) & 0o7755
                chmod(os.path.join(f), mode)
