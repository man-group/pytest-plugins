import sys
import os
from distutils import log

import pkg_resources

from pkglib.manage import is_inhouse_package

from command.base import _banner

BOUND_INF = '99999999'


class DependencyError(Exception):
    """
    Raised for dependency resolution errors
    """
    pass


def is_source_package(pkg):
    """
    True if this is a source checkout
    """
    return not pkg.location.endswith('.egg')


def get_bounds(req):
    """ Return the lower, upper bounds and the open or closed for each bound,
        for a requirement

        Returns
        -------
        (lower, upper, lower_closed?, upper_closed?)

        Examples
        --------
        >>> import pkg_resources
        >>> from pkglib.setuptools.dependency import get_bounds

        >>> r1, r2, r3 = pkg_resources.parse_requirements(['foo','foo==1.2',
                                                           'foo>1.0'])
        >>> get_bounds(r1)
        ('0', '99999999', True, True)
        >>> get_bounds(r2)
        ('1.2', '1.2', True, True)
        >>> get_bounds(r3)
        ('1.0', '99999999', False, True)

        Notes
        -----
        Unsupported for non-final versions.
    """
    upper = BOUND_INF
    lower = '0'
    upper_closed = True
    lower_closed = True
    for _, _, op, version in req.index:
        if op == '==':
            upper = lower = version
            break
        if op in ('>=', '>'):
            lower = version
        elif op  in ('<=', '<'):
            upper = version
        if op == '>':
            lower_closed = False
        elif op == '<':
            upper_closed = False
        # TODO: add support for !=, which is a set of [0(closed) < x(open),
        #                                              x(open) < INF(closed)]
    return lower, upper, lower_closed, upper_closed


class CannotMergeError(Exception):
    """ Raised when we can't merge two sets of requirements
    """


def merge_requirements(r1, r2):
    """ Given two requirements for the same underlying package, attempt to
        merge them into a (possibly more specific) requirement.

        Examples
        --------
        >>> import pkg_resources
        >>> from pkglib.setuptools.dependency import merge_requirements

        >>> r1, r2 = pkg_resources.parse_requirements(['foo==1','foo'])
        >>> merge_requirements(r1,r2)
        Requirement.parse('foo==1')

        >>> r1, r2 = pkg_resources.parse_requirements(['foo==2','foo>2'])
        >>> merge_requirements(r1,r2)
        Traceback (most recent call last):
        ...
        CannotMergeError

        >>> r1, r2 = pkg_resources.parse_requirements(['foo>=1','foo<=3'])
        >>> merge_requirements(r1,r2)
        Requirement.parse('foo>=1,<=3')

        Notes
        -----
        This does not yet support the following
            != operators
            Multi-range sets, like 'foo>2,<4,>6,<7'

    """
    # Catch x>1 vs y
    if r1.key != r2.key:
        raise CannotMergeError

    r1_lower, r1_upper, r1_lower_closed, r1_upper_closed = get_bounds(r1)
    r2_lower, r2_upper, r2_lower_closed, r2_upper_closed = get_bounds(r2)

    r1_lower_parsed = pkg_resources.parse_version(r1_lower)
    r2_lower_parsed = pkg_resources.parse_version(r2_lower)
    r1_upper_parsed = pkg_resources.parse_version(r1_upper)
    r2_upper_parsed = pkg_resources.parse_version(r2_upper)

    # Catch x>2 vs x<1
    if r1_lower_parsed > r2_upper_parsed or r2_lower_parsed > r1_upper_parsed:
        raise CannotMergeError

    # Catch x<3 vs x>4
    if r1_upper_parsed < r2_lower_parsed or r2_upper_parsed < r1_lower_parsed:
        raise CannotMergeError

    # Catch x<4 vs x>=4
    if r1_upper == r2_lower and not (r1_upper_closed and r2_lower_closed):
        raise CannotMergeError

    # Catch x>=4 vs x<4
    if r2_upper == r1_lower and not (r2_upper_closed and r1_lower_closed):
        raise CannotMergeError

    # Catch x>4 vs x<=4
    if r1_lower == r2_upper and not (r1_lower_closed and r2_upper_closed):
        raise CannotMergeError

    # Catch x<=4 vs x>4
    if r2_lower == r1_upper and not (r2_lower_closed and r1_upper_closed):
        raise CannotMergeError

    if r1_lower_parsed >= r2_lower_parsed:
        lower = r1_lower
        lower_closed = r1_lower_closed
    else:
        lower = r2_lower
        lower_closed = r2_lower_closed

    if r1_upper_parsed <= r2_upper_parsed:
        upper = r1_upper
        upper_closed = r1_upper_closed
    else:
        upper = r2_upper
        upper_closed = r2_upper_closed

    # If both requirments have the same numeric bounds, pick whichever is
    # the more restrictive of closed/closed for those bounds
    if r1_lower == r2_lower:
        lower_closed = (r1_lower_closed and r2_lower_closed)

    if r1_upper == r2_upper:
        upper_closed = (r1_upper_closed and r2_upper_closed)

    if lower == upper:
        res = '%s==%s' % (r1.key, lower)

    else:
        specs = []
        if lower != '0':
            if lower_closed:
                specs.append('>=%s' % lower)
            else:
                specs.append('>%s' % lower)

        if upper != BOUND_INF:
            if upper_closed:
                specs.append('<=%s' % upper)
            else:
                specs.append('<%s' % upper)

        res = '%s%s' % (r1.project_name, ','.join(specs))

    return list(pkg_resources.parse_requirements([res]))[0]


def all_packages(exclude_pinned=True, exclusions=None,
                 include_third_party=False):
    """
    Return a lookup of all the installed packages, indexed by name.

    Parameters
    ----------
    exclude_pinned : `bool`
        If set, will exclude any packages that are pinned at a specific version
        by any other package
    exclusions : `list`
        Excludes this list of package names
    include_third_party : `bool`
        If set, will return third-party libraries
    """
    filters = []

    if exclusions:
        filters.append(lambda i: i not in exclusions)

    if not include_third_party:
        filters.append(is_inhouse_package)

    res = [i for i in pkg_resources.working_set]
    for f in filters:
        res = [i for i in res if f(i.project_name)]

    # Filter out pinned packages as well
    if exclude_pinned:
        pinned = pinned_packages(res)
        res = [i for i in res if is_source_package(i) or
               i.project_name not in pinned]

    return (dict(list((i.project_name, i) for i in res)))


def pinned_packages(candidates):
    """
    Return a list of packages that have been pinned at a particular version
    by some other package.
    """
    res = set()

    def req_to_str(pkg, dep):
        spec = ''.join([" ({0} {1}) ".format(req[0], req[1])
                        for req in dep.specs])
        return "{0:20} {1:15} {2}".format(dep.project_name, spec,
                                          pkg.project_name)
    for pkg in candidates:
        [res.add((i.project_name, req_to_str(pkg, i)))
         for i in pkg.requires() if i.specs]
    if res:
        _banner("Pinned packages:")
        log.info("{0:20} {1:15} {2}".format("Name", "Requirement",
                                            "Downstream Package"))
        log.info("{0} {1} {2}" % (20 * '-', 15 * '-', 20 * '-'))
        for i in res:
            log.info(i[1])
    return list(set([i[0] for i in (res)]))


# XXX Refactor this to use get_all_requirements below
def resolve_dependencies(requirements, candidates, seen=None, depth=1,
                         follow_all=False):
    """ Resolve dependencies for this set of requirements

        Parameters
        ----------
        requirements : `list`
            List of requirement strings
        candiates : `list`
            List of candidate packages
        seen : `list`
            List of packages already seen in this search
        depth : `int`
            Search depth
        follow_all : `bool`
            Descend past this depth

        Returns
        -------
        deps : `set`
            Set of all the dependencies for these requirements
    """
    #log.info("resolve deps: reqs: %r follow_all: %r" % (requirements,
    #                                                    follow_all))
    res = set()
    if not seen:
        seen = []

    #indent = ' |  '
    #if [r for r in requirements if r not in seen]:
    #    log.info(depth * indent)
    #else:
    #    log.info((depth - 1) * indent)

    for pkg_name in requirements:
        if pkg_name not in seen and pkg_name in candidates.keys():
            #log.info('%s +---> %s' % ((depth - 1) * indent, pkg_name))
            seen.append(pkg_name)
            pkg = candidates.get(pkg_name, None)
            if pkg:
                res.add(pkg_name)
                if follow_all and pkg.requires():
                    requirements = [i.project_name for i in pkg.requires()]
                    res.update(resolve_dependencies(requirements, candidates,
                                                    seen=seen, depth=depth + 1,
                                                    follow_all=follow_all))
    return res


def get_targets(roots, candidates, everything=False, immediate_deps=True,
                follow_all=True, include_eggs=True, include_source=True):
    """
    Get a list of targets in a dependency graph.
    """
    #log.info("get_targets roots: %r everything: %r deps %r all: %r eggs: %r src: %r" % (
    #              roots, everything, immediate_deps, follow_all, include_eggs, include_source))

    # If we're updating everything, pick all packages that aren't pinned
    if everything:
        targets = candidates.keys()
    else:
        # Resolve the dependency tree for the given root packages
        targets = set(roots)
        for root in roots:
            if immediate_deps:
                requirements = [i.project_name
                                for i in candidates[root].requires()]

                #self.banner("Dependency tree:")
                #log.info(root)
                targets.update(resolve_dependencies(requirements, candidates,
                    seen=[root], follow_all=follow_all))

    source_targets = []
    egg_targets = []

    if include_source:
        source_targets = [i for i in targets
                          if is_source_package(candidates[i])]
    if include_eggs:
        egg_targets = [i for i in targets
                       if not is_source_package(candidates[i])]
    return source_targets, egg_targets


def get_all_requirements(pkg_names):
    """
    Returns the full set of resolved requirements for the given
    package name.

    Parameters
    ----------
    pkg_names : `list`
        List of package names
    """
    env = pkg_resources.Environment(sys.path)
    requirements = []
    for pkg in pkg_names:
        my_dist = [dist for dist in pkg_resources.working_set
                   if pkg == dist.project_name]
        if not my_dist:
            raise DependencyError("Package {0}  is not installed".format(pkg))
        if len(my_dist) != 1:
            raise DependencyError("Package {0} has more than one entry in "
                                  "working set: {1!r}".format(pkg, my_dist))
        requirements.append(my_dist[0].as_requirement())
        env.add(my_dist[0])
    # get all our requirements
    return pkg_resources.WorkingSet([]).resolve(requirements, env)


def get_dist(name, ws=None):
    """ Returns a distribution by name from the given working set.
        Uses the global ws if unspecified.
    """
    if not ws:
        ws = pkg_resources.working_set
    res = [i for i in ws if pkg_resources.safe_name(name) == i.project_name]
    if len(res) > 1:
        raise DependencyError("More than one dist matches the name {0} in "
                              "working set".format(name))
    if res:
        return res[0]
    return None


def get_matching_reqs(ws, dist):
    """ Returns all the reqs from ws that match the dist.
        Also creates backrefs from reqs to dists
    """
    res = []
    for d in ws:
        for r in d.requires():
            if r.project_name == dist.project_name:
                r._dist = d
                res.append(r)
    return res


def remove_from_ws(ws, dist):
    """ Safely removes a dist from a working set
    """
    # This sucks - ws entries might not have resolved symlinks properly, so
    # dist.location != ws.entries[i] even though they point to the same file
    # or directory.
    dist_path = os.path.realpath(dist.location)
    ws_path = dist_path
    for i in ws.entries:
        if os.path.realpath(i) == dist_path:
            ws_path = i
            break
    for path in set([dist_path, ws_path]):
        try:
            ws.entries.remove(path)
        except ValueError:
            pass
        try:
            del(ws.entry_keys[path])
        except KeyError:
            pass
    try:
        del(ws.by_key[dist.key])
    except KeyError:
        pass


def merge_matching_reqs(ws, dist):
    # log.debug('  evaluating dist in working set: %r' % dist)
    # Have a go at trying to figure out why it was installed,
    # by finding all the matching requirements from the ws.
    ws_reqs = get_matching_reqs(ws, dist)
    # log.debug("   requirements from ws that match this dist:")
    # [log.debug("     %s (from %s)" % (i, i._dist)) for i in ws_reqs]

    # Sanity check for conflicts.
    conflicts = [i for i in ws_reqs if dist not in i]
    if conflicts:
        log.warn("This virtualenv is inconsistent - %s is installed "
                 "but there are conflicting requirements:" % dist)
        [log.warn("  %s (from %s)" % (i, i._dist)) for i in conflicts]
        return None
    elif len(ws_reqs) > 1:
        # Now attempt to merge all the requirements from the ws. We do this so
        # that we only count the most specific req when comparing incoming
        # versions.
        try:
            return reduce(merge_requirements, ws_reqs)
        except CannotMergeError:
            log.warn("This virtualenv is inconsistent - %s is installed "
                     "but there are non-mergeable requirements:" % dist)
            [log.warn("  %s (from %s)" % (i, i._dist)) for i in ws_reqs]
            return None
    elif len(ws_reqs) == 1:
        return ws_reqs[0]
    else:
        # log.debug("   no requirements from ws match this dist")

        # We don't know how this package was installed.
        # Set the requirement to a synthetic req which is just the
        # package name, this allows it to be overridden by anything else
        # later on.

        # TODO: keep some sort of record on disk as to why these packages
        #       were installed. Eg, 'pyinstall foo' vs 'pyinstall foo==1.2'
        #       The second invocation should store the full requirement here,
        #       so that the user needs to override their own req manually.
        return pkg_resources.Requirement.parse(dist.project_name)


def get_requirements_from_ws(ws, req_graph):
    """ Given a working set, return a dict of { dist.key -> (dist, req) }
        where req is the merged requirements for this dist, based on the dists
        in the ws.
        This will flag up inconsistent working sets, and trim any dists from
        the ws that are in an inconsistent state.

        It will also fill out edges and nodes on the networkx req_graph.
        child requirements, which is used by the backtracker.
    """
    best = {}
    baseline_reqs = {}
    for dist in ws:
        req = merge_matching_reqs(ws, dist)
        if req is None:
            log.warn("Trimming dist from baseline ws as it's inconsistent: %r",
                     dist)
            remove_from_ws(ws, dist)
        else:
            # log.debug("   best is now (%s): %r" % (req, dist))
            best[req.key] = (dist, req)
            req._chosen_dist = dist
            baseline_reqs[req.key] = req

    # Now fill out the requirements graph.
    # We can do this easily as at this point there is exactly one req for each
    # dist.
    for dist, req in list(best.values()):
        req_graph.add_node(req)
        for r in dist.requires(req.extras):
            if r.key in baseline_reqs:
                req_graph.add_edge(req, baseline_reqs[r.key])
            if r.key not in best:
                log.debug("   unsatisfied dependency %s from %s (from %s)",
                          r, dist, req)
                best[r.key] = (None, r)
                req_graph.add_node(r)

    return best


def get_graph_from_ws(ws):
    """ Converts a working set into a requirements graph.
        This will flag up inconsistant working sets, and trim any dists from
        the ws that are in an inconsistant state.

    Parameters
    ----------
    ws: `pkg_resources.WorkingSet`
        Working set to convert

    Returns
    -------
    (graph, requirements_map)

    graph: `networx.DiGraph` of requirements
    dist_map: Map of { dist.key : (dist, req) } where req is the merged
              requirements for this dist, based on the dists in the ws.
    """
    import networkx
    dist_map = {}
    baseline_reqs = {}
    for dist in ws:
        req = None
        #log.debug('  evaluating dist in working set: %r' % dist)
        # Have a go at trying to figure out why it was installed,
        # by finding all the matching requirements from the ws.
        ws_reqs = get_matching_reqs(ws, dist)
        if ws_reqs:
            #log.debug("   requirements from ws that match this dist:")
            #[log.debug("     %s (from %s)" % (i, i._dist)) for i in ws_reqs]

            # Sanity check for conflicts.
            conflicts = [i for i in ws_reqs if dist not in i]
            if conflicts:
                log.warn("This virtualenv is inconsistant - {0} is installed "
                         "but there are conflicting requirements:"
                         .format(dist))
                [log.warn("  {0} (from {1})".format(i, i._dist))
                 for i in conflicts]
                req = None

            else:
                if len(ws_reqs) > 1:
                    # Now attempt to merge all the requirements from the ws.
                    # We do this so that we only count the most specific req
                    # when comparing incoming versions.
                    try:
                        req = reduce(merge_requirements, ws_reqs)
                    except CannotMergeError:
                        log.warn("This virtualenv is inconsistant - {0} is "
                                 "installed but there are un-mergeable "
                                 "requirements:".format(dist))
                        [log.warn("  {0} (from {1})".format(i, i._dist))
                         for i in ws_reqs]
                        req = None
                else:
                    req = ws_reqs[0]
        else:
            #log.debug("   no requirements from ws match this dist")

            # We don't know how this package was installed.
            # Set the requirement to a synthetic req which is just the
            # package name, this allows it to be overridden by anything else
            # later on.

            # TODO: keep some sort of record on disk as to why these packages
            #       were installed. Eg, 'pyinstall foo' vs 'pyinstall foo==1.2'
            #       The second invocation should store the full requirement
            #       here, so that the user needs to override their own req
            #       manually.
            req = pkg_resources.Requirement.parse(dist.project_name)

        if not req:
            log.warn("Trimming dist from baseline ws as it's inconsistant: "
                     "{0}".format(dist))
            remove_from_ws(ws, dist)
        else:
            dist_map[req.key] = (dist, req)
            # This is important - here we attach the dist that was chosen by
            # this requirement to the req itself
            req._chosen_dist = dist
            baseline_reqs[req.key] = req

    # Now fill out the requirements graph.
    # We can do this easily as at this point there is exactly one req for each
    # dist.
    req_graph = networkx.DiGraph()
    for dist, req in dist_map.values():
        req_graph.add_node(req)
        [req_graph.add_edge(req, baseline_reqs[r.key])
         for r in dist.requires()
         if r.key in baseline_reqs]

    return req_graph, dist_map


def get_all_upstream(graph, req):
    """ Return all upstream requirements in a given graph
    """
    from networkx import algorithms
    # dfs_successors returns a dict representing the edges its found.
    # Flatten it.
    res = algorithms.dfs_successors(graph, req)
    res = set(res.keys() + [i for j in res.values() for i in j])
    return res


def get_all_downstream(graph, req):
    """ Return all downstream requirements in a given graph
    """
    # Predecessor algorithms don't do what I would expect... had to
    # implement my own here.
    found = set()

    def descend(r):
        found.add(r)
        for ds in graph.predecessors(r):
            if ds not in found:
                descend(ds)
    descend(req)
    return found


def get_backtrack_targets(graph, req):
    """ Walk through a graph of requirements, returning all the
        other requirements that were generated by this one, unless they
        are also needed by unrelated requirements.

        This is used when we're replacing one version of something in the
        graph with another, and we want to pull out all the outgoing version's
        dependencies so they don't conflict with the incoming one.

        Eg::
             D      A depends on B, C. B and C depend on D. E depends on C.
            / \     If we're backtracking A, then we start by finding all
           B   C    upstream from A = (A, B, C, D). Then, search for all
            \ / \   nodes not in (A, B, C, D) = (E), and find their
             A   E  upstreams = (E, C, D). The final result is the first
                    set minus the second = (A, B, C, D) - (E, C, D)
                     == (A, B)

        Another example::

             D__    We're backtracking A as before, but there A has a couple
            / \ \   of downstream dependencies as well. If we just ran the
           B   C |  above algo we'd not backtrack anything as A is an upstream
            \ /  |  dependency of some other nodes and therefore this shadows
             A   |  all of A's upstream targets.
            / \ /   Because we know we're going to remove least A regardless,
           E   F    we can disregard direct downstream links from A.
                    In this example this is E-A and F-A. The only case where
                    this fails if there are implicit dependencies - ie, E
                    imports code from B, without declaring an explicit
                    dependency on B (rather it relies on A to bring it in).

                    In this example the search should return (A, B, C).
    """
    log.debug("******   resolving backtrack targets")

    # Uncomment to debug graphically
    #import graph as graphing
    #graphing.draw_networkx_with_pydot(graph, include_third_party=True,
    #                                  show_reqs=True)

    # First take a copy of the graph and remove direct downstream deps to
    # cater for the second case in the docstring.
    graph = graph.copy()

    direct_predecessors = graph.predecessors(req)
    if direct_predecessors:
        log.debug("******   ignoring direct predecessors:")
        [log.debug("******     {0}".format(i)) for i in direct_predecessors]

        graph.remove_edges_from([(i, req) for i in direct_predecessors])
        #graphing.draw_networkx_with_pydot(graph, include_third_party=True,
        #                                  show_reqs=True)

    def resolved_set(iterable):
        """ Filter out reqs that havent yet been resolved """
        return set([i for i in iterable if hasattr(i, '_chosen_dist')])

    # This is (A, B, C, D) in the first docstring example
    upstream = resolved_set(get_all_upstream(graph, req))

    #log.debug("******   upstream reqs:")
    #[log.debug("******     {0}".format(i)) for i in upstream]

    # This is (E) in the first docstring example
    unrelated = resolved_set(graph.nodes()).difference(upstream)
    #log.debug("******   unrelated reqs:")
    #[log.debug("******     {0}".format(i)) for i in unrelated]

    # This is (C, D, E) in the first docstring example
    no_touchies = set([j for i in unrelated
                       for j in resolved_set(get_all_upstream(graph, i))])
    #log.debug("******   unrelated upstream reqs:")
    #[log.debug("******     {0}".format(i)) for i in no_touchies]

    # This is (A, B, D) in the first docstring example
    res = upstream.difference(no_touchies)
    log.debug("******   result:")
    [log.debug("******     {0} ({1})".format(i, i._chosen_dist)) for i in res]

    return res
