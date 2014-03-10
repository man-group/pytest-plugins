import sys
import os
from distutils import log
import collections

import pkg_resources

from pkglib import pyenv, util

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
        elif op in ('<=', '<'):
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


def check_version_bounds(r1l, r1lc, r1u, r1uc, r2l, r2lc, r2u, r2uc):
    """
    Checks version bounds for validity. Ensures that requirement ranges
    are not mutually exclusive and can be merged.

    Parameters
    ----------
    r1l : `str`
        lower bound of the version range for the first requirement
    r1lc : `bool`
        a flag indicating whether lower bound for the first requirement
        is closed
    r1u : `str`
        upper bound of the version range for the first requirement
    r1uc : `bool`
        a flag indicating whether upper bound for the first requirement
        is closed
    r2l : `str`
        lower bound of the version range for the second requirement
    r2lc : `bool`
        a flag indicating whether lower bound for the second requirement
        is closed
    r2u : `str`
        upper bound of the version range for the second requirement
    r2uc : `bool`
        a flag indicating whether upper bound for the second requirement
        is closed

    Returns
    -------
    parse_versions : `tuple`
        contains parsed versions of requirements in the following order:
        - first requirement lower bound
        - first requirement upper bound
        - second requirement lower bound
        - second requirement upper bound
    """
    r1lp = pkg_resources.parse_version(r1l)
    r1up = pkg_resources.parse_version(r1u)
    r2lp = pkg_resources.parse_version(r2l)
    r2up = pkg_resources.parse_version(r2u)

    # Catch x>2 vs x<1
    if r1lp > r2up or r2lp > r1up:
        raise CannotMergeError

    # Catch x<3 vs x>4
    if r1up < r2lp or r2up < r1lp:
        raise CannotMergeError

    # Catch x<4 vs x>=4
    if r1u == r2l and not (r1uc and r2lc):
        raise CannotMergeError

    # Catch x>=4 vs x<4
    if r2u == r1l and not (r2uc and r1lc):
        raise CannotMergeError

    # Catch x>4 vs x<=4
    if r1l == r2u and not (r1lc and r2uc):
        raise CannotMergeError

    # Catch x<=4 vs x>4
    if r2l == r1u and not (r2lc and r1uc):
        raise CannotMergeError

    return r1lp, r1up, r2lp, r2up


def construct_req_from_specs(r, l, u, lc, uc, extras=[]):
    extras = "[%s]" % ",".join(extras) if extras else ""

    if l == u:
        res = '%s==%s' % (r.project_name + extras, l)

    else:
        specs = []
        if l != '0':
            if lc:
                specs.append('>=%s' % l)
            else:
                specs.append('>%s' % l)

        if u != BOUND_INF:
            if uc:
                specs.append('<=%s' % u)
            else:
                specs.append('<%s' % u)

        res = '%s%s' % (r.project_name + extras, ','.join(specs))

    return pkg_resources.Requirement.parse(res)


def merge_requirements(r1, r2):
    """ Given two requirements for the same underlying package, attempt to
        merge them into a (possibly more specific) requirement.

        Examples
        --------
        >>> import pkg_resources
        >>> from pkglib.setuptools.dependency import merge_requirements
        >>> from pkglib.setuptools.dependency import CannotMergeError

        >>> r1, r2 = pkg_resources.parse_requirements(['foo==1','foo'])
        >>> merge_requirements(r1,r2)
        Requirement.parse('foo==1')

        >>> r1, r2 = pkg_resources.parse_requirements(['foo==2','foo>2'])
        >>> try:
        ...     merge_requirements(r1,r2)
        ...     raise AssertionError("CannotMergeError exception not raised")
        ... except CannotMergeError as ex:
        ...     pass

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

    r1l, r1u, r1lc, r1uc = get_bounds(r1)
    r2l, r2u, r2lc, r2uc = get_bounds(r2)

    r1lp, r1up, r2lp, r2up = check_version_bounds(r1l, r1lc, r1u, r1uc,
                                                  r2l, r2lc, r2u, r2uc)

    if r1lp >= r2lp:
        l = r1l
        lc = r1lc
    else:
        l = r2l
        lc = r2lc

    if r1up <= r2up:
        u = r1u
        uc = r1uc
    else:
        u = r2u
        uc = r2uc

    # If both requirments have the same numeric bounds, pick whichever is
    # the more restrictive of closed/closed for those bounds
    if r1l == r2l:
        lc = (r1lc and r2lc)

    if r1u == r2u:
        uc = (r1uc and r2uc)

    extras = set(r1.extras).union(r2.extras)
    return construct_req_from_specs(r1, l, u, lc, uc, extras)


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
        filters.append(util.is_inhouse_package)

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
    res = set()
    if not seen:
        seen = []

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


def get_targets(roots, candidates, everything=False):
    """
    Get a list of targets in a dependency graph.
    """
    # If we're updating everything, pick all packages that aren't pinned
    return (candidates.keys() if everything
            else resolve_dependencies(roots, candidates, follow_all=True))


def get_all_requirements(pkg_names, ignore_explicit_builtins=False):
    """
    Returns the full set of requirements for the given package name.

    Parameters
    ----------
    pkg_names : `list`
        List of package names
    ignore_explicit_builtins : `bool`
        whether to remove requirements which are available as a
        built-in of the current Python interpreter. I am looking
        at you, importlib.

    Returns
    -------
    requriements : `list` of `Distribution`
    """
    env = pkg_resources.Environment(sys.path)
    requirements = []
    for pkg in pkg_names:
        my_dist = [dist for dist in pkg_resources.working_set
                   if pkg == dist.project_name]
        if not my_dist:
            raise DependencyError("Package %s is not installed" % pkg)
        if len(my_dist) != 1:
            raise DependencyError("Package %s has more than one entry in "
                                  "working set: %r" % (pkg, my_dist))
        my_dist = my_dist[0]
        requirements.append(my_dist.as_requirement())
        if ignore_explicit_builtins and my_dist.requires():
            my_dist_original = my_dist
            my_dist = my_dist_original.clone()
            my_dist.requires = (lambda *_1, **_2:
                                [r for r in my_dist_original.requires() if not
                                 pyenv.included_in_batteries(r, sys.version_info)])
            if ((my_dist.key in env and
                 my_dist.requires() != my_dist_original.requires())):
                env.remove(my_dist)

        env.add(my_dist)

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

    res = set([])

    # find all distributions whose extras are referenced
    extras = collections.defaultdict(set)  # project_name -> set of referenced extras
    for req in (r for d in ws for r in d.requires() if r.extras):
        for e in req.extras:
            extras[req.project_name].add(e)

    for d in ws:
        for r in d.requires(extras.get(d.project_name, [])):
            if r.project_name == dist.project_name:
                r._dist = d
                res.add(r)

    return list(res)


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


def remove_from_ws(ws, dist):
    """ Safely removes a dist from a working set
    """
    # TODO: fix the path issues below, re-instate realpath matching

    # This sucks - ws entries might not have resolved symlinks properly, so
    # dist.location != ws.entries[i] even though they point to the same file
    # or directory.

#     dist_path = os.path.realpath(dist.location)
#     ws_path = dist_path
#     for i in ws.entries:
#         if os.path.realpath(i) == dist_path:
#             ws_path = i
#             break
#     import pdb; pdb.set_trace()
#     for path in set([dist_path, ws_path, dist.location]):
#         try:
#             ws.entries.remove(path)
#         except ValueError:
#             pass
#         try:
#             del(ws.entry_keys[path])
#         except KeyError:
#             pass
#     try:
#         del(ws.by_key[dist.key])
#     except KeyError:
#         pass

    if dist.location in ws.entries or ws.entry_keys:
        if dist.location in ws.entries:
            ws.entries.remove(dist.location)
        if dist.location in ws.entry_keys:
            del(ws.entry_keys[dist.location])
        for entry, keys in ws.entry_keys.items():
            if dist.key in keys:
                keys.remove(dist.key)
                if not keys:
                    ws.entries.remove(entry)
        if dist.key in ws.by_key:
            del(ws.by_key[dist.key])


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
        req = merge_matching_reqs(ws, dist)
        if req is None:
            log.warn("Trimming dist from baseline ws as it's inconsistent: %r",
                     dist)
            remove_from_ws(ws, dist)
        else:
            # log.debug("   best is now (%s): %r" % (req, dist))
            dist_map[req.key] = (dist, req)
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
    """ Walk through a graph of requirements, returning a two sets of
        requirements:
            1) all the other requirements that were generated by this one,
               unless they are also needed by unrelated requirements
            2) all the other requirements that were generated by this one,
               and also needed by unrelated requirements - I call this 'shadowing'.

        This is used when we're replacing one version of something in the
        graph with another, and we want to pull out all the outgoing version's
        dependencies so they don't conflict with the incoming one.

        An important post-step is to re-evaluate all the 'previous best'
        requirements for the 'shadowed' packages. This stops package upgrades
        getting conflicted with previous iterations of themselves.

        Eg::
             D      A depends on B, C. B and C depend on D. E depends on C.
            / \     If we're backtracking A, then we start by finding all
           B   C    upstream from A = (A, B, C, D). Then, search for all
            \ / \   nodes not in (A, B, C, D) = (E), and find their
             A   E  upstreams = (E, C, D). The final result is the first
                    set minus the second = (A, B, C, D) - (E, C, D)
                     == (A, B). The shadowed packages are (C, D).

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

                    In this example the search should return (A, B, C), and
                    the shadowed packages are (D).
    """
    log.debug("******   resolving backtrack targets")

    # Uncomment to debug graphically
    # import graph as graphing
    # graphing.draw_networkx_with_pydot(graph, include_third_party=True,
    #                                  show_reqs=True)

    # First take a copy of the graph and remove direct downstream deps to
    # cater for the second case in the docstring.
    graph = graph.copy()

    direct_predecessors = graph.predecessors(req)
    if direct_predecessors:
        log.debug("******   ignoring direct predecessors:")
        [log.debug("******     {0}".format(i)) for i in direct_predecessors]

        graph.remove_edges_from([(i, req) for i in direct_predecessors])
        # graphing.draw_networkx_with_pydot(graph, include_third_party=True,
        #                                  show_reqs=True)

    def resolved_set(iterable):
        """ Filter out reqs that havent yet been resolved """
        return set([i for i in iterable if hasattr(i, '_chosen_dist')])

    # This is (A, B, C, D) in the first docstring example
    upstream = resolved_set(get_all_upstream(graph, req))

    log.debug("******   upstream reqs:")
    [log.debug("******     {0}".format(i)) for i in upstream]

    # This is (E) in the first docstring example
    unrelated = resolved_set(graph.nodes()).difference(upstream)
    log.debug("******   unrelated reqs:")
    [log.debug("******     {0}".format(i)) for i in unrelated]

    # This is (C, D, E) in the first docstring example
    no_touchies = set([j for i in unrelated
                       for j in resolved_set(get_all_upstream(graph, i))])
    log.debug("******   upstream reqs shadowed by unrelated reqs:")
    [log.debug("******     {0}".format(i)) for i in no_touchies]

    # This is (A, B, D) in the first docstring example
    res = upstream.difference(no_touchies)
    log.debug("******   result:")
    [log.debug("******     {0} ({1})".format(i, i._chosen_dist)) for i in res]

    return res, no_touchies
