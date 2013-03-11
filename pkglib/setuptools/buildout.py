""" ZC.Buildout helper module.
"""
import sys
import os
import shutil
import stat
import logging
import copy
import operator
from distutils import log
from distutils.errors import DistutilsOptionError

import pkg_resources
from zc.buildout import easy_install
from path import path as _p
from pip.util import is_local
from setuptools.command.easy_install import chmod

from pkglib import manage, CONFIG
import dependency
import graph

logger = logging.getLogger('zc.buildout.easy_install')


############ TODO: #################################################
#  Refactor this whole mouule so to remove the depencency on
#  zc.buildout. We have done enough work now to customise
#  the install behavior so that we don't need it anymore,
#  and we're having to put in hacks to make it work like distribute.
#  The 'install' method below could be moved to an override of the
#  WorkingSet.resolve method.
#
####################################################################


class Installer(easy_install.Installer):
    """  Override some functionality of the buildout installer,
         particularly the way it always chooses develop eggs over
         all other dist choices.
    """

    def update_search_path(self):
        """ Add our module search paths to the installer so we can source eggs
            from local disk. Uses CONFIG.installer_search_path, and scans one
            directory deep within each path component.
        """
        search_path = CONFIG.installer_search_path
        if search_path:
            log.info("Scanning virtualenv search path {0}.."
                     .format(search_path))
            for path_component in [_p(i) for i in search_path]:
                if path_component.exists():
                    self._env.scan([path_component] + path_component.dirs())
            log.info("Done")

    def _satisfied(self, req, source=None):
        """  Modified version of the buildout version. Changes:
             - Always choose develop eggs if we find them in site_packages.
             - Prefer dev versions of eggs from the package server over final
               version in environment (esp from CONFIG.installer_search_path)
        """
        dists = [dist for dist in self._env[req.project_name] if (
                    dist in req and (
                        dist.location not in self._site_packages or
                        self.allow_site_package_egg(dist.project_name)))]
        if not dists:
            log.debug('We have no distributions for %s that satisfies %r.',
                         req.project_name, str(req))
            return None, self._obtain(req, source)

        # Look for develop eggs - we always use these if we find them so that
        # source checkouts are 'sacrosanct'
        for dist in dists:
            if (dist.precedence == pkg_resources.DEVELOP_DIST):
                log.debug('We have a develop egg: %s', dist)
                return dist, None

        # Special common case, we have a specification for a single version:
        specs = req.specs
        if len(specs) == 1 and specs[0][0] == '==':
            log.debug('We have the distribution that satisfies %r.',
                         str(req))
            return dists[0], None

        # Filter the eggs found in the environment for final/dev
        version_comparitor = self.get_version_comparitor(req)
        preferred_dists = [dist for dist in dists
                           if version_comparitor(dist.parsed_version)]

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
                'There are no distros available that meet %r.\n'
                'Using our best, %s.',
                str(req), best_available)
            return best_we_have, None

        # Now pick between the version from the index server and the version
        # found in our environment. We put the environment one first here
        # so that if they're the same version, it will pick that one and we're
        # not downloading things unnecessarily
        best = self.choose_between(best_we_have, best_available,
                                   version_comparitor)
        if best == best_available:
            log.debug("Chose dist from index server: {0}".format(best))
            return None, best

        log.debug("Chose dist from environment: {0}".format(best_we_have))
        return best_we_have, None

    def choose_between(self, d1, d2, comparitor):
        """ Choose between two different dists, given a dev/final comparitor.
            If both d1 and d2 have the same version, it will return d1.
        """
        d1_preferred = comparitor(d1.parsed_version)
        d2_preferred = comparitor(d2.parsed_version)
        key = operator.attrgetter('parsed_version')

        log.debug("Choosing between versions {0} and {1}"
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
            distribute and this comes via pkglib and friends.
            Blanking this out will supress a bunch of spurious warnings.
        """
        pass

    def get_backtrack_targets(self, req_graph, req, results=None):
        """ Walk through a graph of requirements, returning all the
            other requirements that were generated by this one
        """
        if results is None:
            results = set()

        log.debug("       found %r" % req)
        results.add(req)
        for upstream in req_graph.successors(req):
            if upstream not in results:
                self.get_backtrack_targets(req_graph, upstream, results)
        return results

    def install(self, specs, working_set=None, use_existing=False,
                draw_graph=False):
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
        import networkx
        # TODO: break this method down into manageable chunks.
        log.debug('Installing requirements: %s', repr(specs)[1:-1])

        # This is a set of processed requirements.
        processed = {}

        # This is the graph of requirements
        req_graph = networkx.DiGraph()

        # This is the list of stuff we've installed, to hand off to the
        # postinstall steps like egg-link etc
        setup_dists = pkg_resources.WorkingSet([])

        path = self._path
        destination = self._dest
        if destination is not None and destination not in path:
            path.insert(0, destination)

        requirements = [self._constrain(pkg_resources.Requirement.parse(spec))
                        for spec in specs]

        if working_set is None:
            ws = pkg_resources.WorkingSet([])
        else:
            # Make a copy, we don't want to mess up the global w/s if this is
            # what's been passed in.
            ws = pkg_resources.WorkingSet(working_set.entries)

        # First we need to get a map of requirements for what is currently
        # installed. This is so we can play them off against new requirements.

        # For simplicity's sake, we merge all requirements matching installed
        # packages into a single requirement. This also mimics how the packages
        # would have been installed in the first place.

        # This is a mapping of key -> (dist, originating req) which is our best
        # found so far.
        best = dependency.get_requirements_from_ws(ws, req_graph)

        log.debug("Baseline working set: (merged req, dist)")
        for dist, req in best.values():
            log.debug("   %25s: %r" % (req, dist))

        if draw_graph:
            graph.draw_networkx_with_pydot(req_graph, True)

        # Set up the stack, so we're popping from the front
        requirements.reverse()

        # This is our 'baseline' set of packages. Anything we've picked that
        # isn't in here, hasn't yet been fully installed.
        baseline = copy.copy(ws.entries)
        env = pkg_resources.Environment(baseline)

        def purge_req(req):
            """ Purge a requirement from all our indexes, used for
                backtracking
            """
            if req.key in best:
                del best[req.key]
            [dependency.remove_from_ws(w, req._chosen_dist)
             for w in (ws, setup_dists) if req._chosen_dist in w]

        while requirements:
            # Process dependencies breadth-first.
            req = self._constrain(requirements.pop(0))
            if req in processed:
                # Ignore cyclic or redundant dependencies.
                continue

            # Add the req to the graph
            req_graph.add_node(req)

            log.debug('Processing %r' % req)
            for r in req_graph.predecessors(req):
                log.debug(' -- downstream: %r' % r)

            dist, prev_req = best.get(req.key, (None, None))
            log.debug("  previous best is %r (%r) " % (dist, prev_req))

            if dist is None:
                # Find the best distribution and add it to the map.
                dist = ws.by_key.get(req.key)
                if dist is None:
                    try:
                        dist = env.best_match(req, ws)
                    except pkg_resources.VersionConflict, err:
                        raise easy_install.VersionConflict(err, ws)

                    log.debug("  env best match is %r " % (dist))
                    if dist is None or (
                        dist.location in self._site_packages and not
                        self.allow_site_package_egg(dist.project_name)):
                        # If we didn't find a distribution in the
                        # environment, or what we found is from site
                        # packages and not allowed to be there, try
                        # again.
                        if destination:
                            log.debug('  getting required %r', str(req))
                        else:
                            log.debug('  adding required %r', str(req))
                        easy_install._log_requirement(ws, req)
                        for dist in self._get_dist(req,
                                                   ws, self._always_unzip):
                            ws.add(dist)
                            log.debug('  adding dist to target installs: %r',
                                      dist)
                            setup_dists.add(dist)
                    else:
                        # We get here when things are in the egg cache, or
                        # deactivated in site-packages. Need to add to
                        # the working set or they don't get setup properly.
                        log.debug('  dist in environ: %r' % dist)
                        ws.add(dist)
                        setup_dists.add(dist)
                        log.debug('  adding dist to target installs: %r', dist)

                    best[req.key] = (dist, req)
                    log.debug("   best is now (%s): %r" % (req, dist))
                else:
                    log.debug('  dist in working set: %r' % dist)
                    # We get here when the dist was already installed.
                    # TODO: check we don't need this
                    #setup_dists.add(dist)

            else:
                log.debug('  already have dist: %r' % dist)

            if prev_req and prev_req.hashCmp != req.hashCmp:
                log.debug("--- checking previously requirements: %s vs %s" %
                          (prev_req, req))
                # Here is where we can possibly backtrack in our graph walking.

                # We need to check if we can merge the new requirement with
                # ones  that we found previously. This merging is done on the
                # rules of specivicity - ie, creating a new requirement that is
                # bounded by the most specific specs from both old and new.
                try:
                    merged_req = dependency.merge_requirements(prev_req, req)
                    log.debug("--- merged requirement: %s" % merged_req)

                    if dist in merged_req:
                        # The dist we've already picked matches the more new
                        # req, just update the 'best' index to the new one
                        if prev_req.hashCmp != merged_req.hashCmp:
                            log.debug("--- upgrading to more specific "
                                      "requirement %s -> %s" % (prev_req,
                                                                merged_req))
                            best[req.key] = (dist, merged_req)
                            req = merged_req

                            # Add a new node in our graph for the merged 
                            # requirement.
                            req_graph.add_node(req)
                            upstream = req_graph.successors(prev_req)
                            if upstream:
                                log.debug("---- adding edges from %s to %s" %
                                          (req, upstream))
                                [req_graph.add_edge(req, i) for i in upstream]
                        else:
                            log.debug("--- skipping %s, it's more general than"
                                      " %s" % (req, prev_req))
                            processed[req] = True
                            continue
                            # TODO: look @ req.extras?
                    else:
                        # The more specific version is different to what we've
                        # already found, we need to override it.
                        log.debug("**** overriding requirement %r with %r" %
                                  (prev_req, req))

                        # Now we need to purge the old package and everything
                        # it brought in, so that there's no chance of conflicts
                        # with the new version we're about to install

                        log.debug("****   resolving possible backtrack "
                                  "targets")

                        upstream_reqs = dependency.get_all_upstream(req_graph,
                                                                    prev_req)

                        for upstream_req in upstream_reqs:
                            if not hasattr(upstream_req, '_chosen_dist'):
                                continue
                            upstream_dist = upstream_req._chosen_dist

                            # TODO : find a way to warn users here that makes sense, doing this for
                            #        every package is misleading, as a lot of them will get re-chosen
                            #        by the new requirement

                            #if target_dist.location in baseline:
                            #    log.debug("**** target in baseline, we may be changing the environment")

                            if upstream_dist in ws or upstream_dist in setup_dists:
                                log.debug("**** pulling out backtrack target: %r" % upstream_dist)

                                # XXX this isn't working properly yet
                                # We need to check if there was more than one downstream
                                # source for this target, so that we're only pulling out the minimal
                                # set of packages from the graph.
                                #downstream_diffs = dependency.get_downstream_difference(
                                #            req_graph, upstream_req, prev_req)

                                #if downstream_diffs:
                                #    log.debug("**** %r has other downstream parents: %r" %
                                #              (upstream_dist, downstream_diffs))
                                #else:
                                # ...  do the purging

                            purge_req(upstream_req)

                        # Now purge the requirement we're replacing
                        purge_req(prev_req)

                        # Push the updated req back to the front of the queue
                        requirements.insert(0, merged_req)
                        continue

                except dependency.CannotMergeError:
                    log.debug("--- cannot merge requirements")
                    pass

            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency.
                raise easy_install.VersionConflict(
                    pkg_resources.VersionConflict(dist, req), ws)

            # If we get to this point, we're happy with this requirement and the distribution
            # that has been found for it. Store a reference to this mapping, so we can get back
            # to it if we need to backtrack.
            req._chosen_dist = dist

            for new_req in dist.requires(req.extras)[::-1]:
                if not self._constrain(new_req) in processed.keys() + requirements:
                    log.debug('  new requirement: %s' % new_req)
                    requirements.append(new_req)

                    # Add the new requirements into the graph
                    req_graph.add_node(new_req)

                    # And an edge for the new req
                    req_graph.add_edge(req, new_req)

            processed[req] = True
            if dist.location in self._site_packages:
                log.debug('  egg from site-packages: %s', dist)
            log.debug('  finished processing %s' % req)

        # Now trim dists to set-up down to things that weren't already installed. This cuts
        # down all the spurious 'adding xyz to easy-install.pth messages' not to mention loads
        # of I/O.
        setup_dists = [i for i in setup_dists if i not in pkg_resources.working_set]

        log.debug('Finished processing.')

        return setup_dists

    def get_version_comparitor(self, requirement):
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
        if manage.is_inhouse_package(requirement.project_name):
            if self._prefer_final:
                log.debug('  in-house package, prefer-final')
                return easy_install._final_version
            else:
                log.debug('  in-house package, prefer-dev')
                return self.is_dev_version
        else:
            log.debug('  third-party package, always prefer-final')
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
        dists = [dist for dist in index[requirement.project_name] if (
                    dist in requirement and (
                        dist.location not in self._site_packages or
                        self.allow_site_package_egg(dist.project_name))
                    and (
                        (not source) or
                        (dist.precedence == pkg_resources.SOURCE_DIST))
                    )
                 ]

        # Filter for final/dev and use the result if it is non empty.
        version_comparitor = self.get_version_comparitor(requirement)
        filtered_dists = [dist for dist in dists
                          if version_comparitor(dist.parsed_version)]
        if filtered_dists:
            log.debug('  filtered to {0}'.format(filtered_dists))
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

        log.debug('  best picks are {0}'.format(best))

        if not best:
            return None
        if len(best) == 1:
            return best[0]
        if self._download_cache:
            for dist in best:
                if (easy_install.realpath(os.path.dirname(dist.location)) ==
                    self._download_cache):
                    return dist
        best.sort()
        return best[-1]


def uninstall_eggs(reqs):
    """ Remove eggs matching the given requirements.
    """
    # XXX This doesn't do dependencies?
    dists = []
    names = [i.project_name for i in pkg_resources.parse_requirements(reqs)]
    for name in names:
        dist = [d for d in pkg_resources.working_set if d.project_name == name]
        if not dist:
            raise DistutilsOptionError('Cannot remove package not yet '
                                       'installed: %s' % name)
        dist = dist[0]
        if not dist.location.endswith('.egg'):
            raise DistutilsOptionError('Not an egg at %s, chickening out' %
                                       dist.location)
        if is_local(dist.location):
            dists.append(dist)
        else:
            log.info("Not uninstalling egg, it's not in our virtualenv: %s" %
                     dist.location)

    for dist in dists:
        log.info("Removing %s (%s)" % (dist, dist.location))
        shutil.rmtree(dist.location)
        dependency.remove_from_ws(pkg_resources.working_set, dist)


def install(cmd, reqs, add_to_global=False, prefer_final=True,
            force_upgrade=False, use_existing=False):
    """ Installs a given requirement using buildout's modified easy_install.

        Parameters
        ----------
        cmd : `setuptools.Command`
           active setuptools Cox8mmand class
        reqs : `list`
           list of distutils requirements, eg ['foo==1.2']
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

    # Now apply our runtime additions to its working environment. This includes
    # adding eggs for the egg cache, and removing eggs that we're forcing to be
    # upgraded.

    installer.update_search_path()

    # This is a bit nasty - we have to monkey-patch the filter for final
    # versions so that we can also filter for dev versions as well.

    # Set prefer_final to True, always, so it enables the filter
    easy_install.prefer_final(True)

    # This returns a WorkingSet of the packages we just installed.
    ws = None
    if use_existing:
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
    # also in install_requires. Because these are classed as 'already
    # installed' by the installer, they won't have been added to the workingset
    # of packages to set-up in the next step.

    # Here we ensure that they're added in along with any of their
    # own dependencies if they are also part of the package install_requires.
    # FIXME: this won't pick up non-direct dependencies.
    #        Eg: setup_requires = numpy,
    #            install_requires = something that has numpy as a dependency
    def also_required(dist):
        for req in pkg_resources.parse_requirements(reqs):
            if dist in req:
                return True
        return False

    setup_dists = [i for i in pkg_resources.working_set.resolve(
                                    get_setup_requires(cmd.distribution))
                   if also_required(i)]

    if setup_dists:
        log.debug("setup_requires distributions to be set-up:")
        [log.debug("  %r" % i) for i in setup_dists]

    # Now run the installer
    try:
        to_setup = installer.install(reqs, working_set=ws,
                                     use_existing=use_existing)
    except easy_install.MissingDistribution, e:
        log.error(e)
        # TODO: call missing distro hook here
        sys.exit(1)

    # Add any of the setup_requires dists to be set-up.
    to_setup = set(to_setup + setup_dists)
    if to_setup:
        log.debug('Packages to set-up:')
        for i in to_setup:
            log.debug(' %r' % i)

        # Now we selectively run setuptool's post-install steps.
        # Luckily, the buildout installer didnt strip off any of the useful
        # metadata about the console scripts.
        for dist in to_setup:
            if dist.location.startswith(manage.get_site_packages()):
                fix_permissions(dist)
            cmd.process_distribution(None, dist, deps=False)
            # Add the distributions to the global registry if we asked for it.
            # This makes the distro importable, and classed as 'already
            # installed' by the dependency resolution algorithm.
            if add_to_global:
                pkg_resources.working_set.add(dist)
    else:
        log.debug('Nothing to set-up.')
    return to_setup


def fix_permissions(dist):
    """ Buildout doesn't fix the package permissions like easy_install, here
        we replicate distributes's method at easy_install.unpack_and_compile
    """
    for root, _, files in os.walk(dist.location):
        for f in [os.path.join(root, i) for i in files]:
            if f.endswith('.py') or f.endswith('.dll') or \
               f.endswith('.so') and not 'EGG-INFO' in f:
                mode = ((os.stat(f)[stat.ST_MODE]) | 0555) & 07755
                chmod(os.path.join(f), mode)


def get_setup_requires(dist):
    """ Get the setup_requires from a distribution, these are unhelpfully
        not stored like the install_requires and test_requires
    """
    reqs = dist.command_options.get('metadata', {}).get('setup_requires')
    if reqs:
        return pkg_resources.parse_requirements([i.strip()
                                                 for i in reqs[1].split('\n')
                                                 if i.strip()])
    return []
