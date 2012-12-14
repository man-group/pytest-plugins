import sys

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
    """ Return the lower, upper bounds and the open or closed for each bound, for a requirement

        Returns
        -------
        (lower, upper, lower_closed?, upper_closed?)

        Examples
        --------
        >>> import pkg_resources
        >>> from pkglib.setuptools.dependency import get_bounds

        >>> r1, r2, r3 = pkg_resources.parse_requirements(['foo','foo==1.2','foo>1.0'])
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
        # TODO: add support for !=, which is a set of [0(closed) < x(open), x(open) < INF(closed)]
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


def all_packages(exclude_pinned=True, exclusions=None, include_third_party=False):
    """
    Return a lookup of all the installed packages, indexed by name.

    Parameters
    ----------
    exclude_pinned : `bool`
        If set, will exclude any packages that are pinned at a specific version by
        any other package
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
        spec = ''.join([" (%s %s) " % (req[0], req[1]) for req in dep.specs])
        return "%20s %15s %s" % (dep.project_name, spec, pkg.project_name)
    for pkg in candidates:
        [res.add((i.project_name, req_to_str(pkg, i))) for i in pkg.requires() if i.specs]
    if res:
        _banner("Pinned packages:")
        log.info("%20s %15s %s" % ("Name", "Requirement", "Downstream Package"))
        log.info("%s %s %s" % (20 * '-', 15 * '-', 20 * '-'))
        for i in res:
            log.info(i[1])
    return list(set([i[0] for i in (res)]))


# XXX Refactor this to use get_all_requirements below
def resolve_dependencies(requirements, candidates, seen=None, depth=1, follow_all=False):
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
    #log.info("resolve deps: reqs: %r follow_all: %r" % (requirements, follow_all))
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


def get_targets(roots, candidates, everything=False, immediate_deps=True, follow_all=True,
                include_eggs=True, include_source=True):
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
                requirements = [i.project_name for i in candidates[root].requires()]

                #self.banner("Dependency tree:")
                #log.info(root)
                targets.update(resolve_dependencies(requirements, candidates,
                    seen=[root], follow_all=follow_all))

    source_targets = []
    egg_targets = []

    if include_source:
        source_targets = [i for i in targets if is_source_package(candidates[i])]
    if include_eggs:
        egg_targets = [i for i in targets if not is_source_package(candidates[i])]
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
        my_dist = [dist for dist in pkg_resources.working_set if pkg == dist.project_name]
        if not my_dist:
            raise DependencyError("Package %s is not installed" % pkg)
        if len(my_dist) != 1:
            raise DependencyError("Package %s has more than one entry in working set: %r" %
                                  (pkg, my_dist))
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
        raise DependencyError("More than one dist matches the name %r in working set" % name)
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
    if dist.location in ws.entries or ws.entry_keys:
        if dist.location in ws.entries:
            ws.entries.remove(dist.location)
        if dist.location in ws.entry_keys:
            del(ws.entry_keys[dist.location])
        if dist.key in ws.by_key:
            del(ws.by_key[dist.key])


def get_requirements_from_ws(ws, req_graph):
    """ Given a working set, return a dict of { dist.key -> (dist, req) }
        where req is the merged requirements for this dist, based on the dists
        in the ws.
        This will flag up inconsistant working sets, and trim any dists from
        the ws that are in an inconsistant state.

        It will also fill out edges and nodes on the networkx req_graph.
        child requirements, which is used by the backtracker.
    """
    best = {}
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
                log.warn("This virtualenv is inconsistant - %s is installed but there are "
                         "conflicting requirements:" % dist)
                [log.warn("  %s (from %s)" % (i, i._dist)) for i in conflicts]
                req = None

            else:
                if len(ws_reqs) > 1:
                    # Now attempt to merge all the requirements from the ws. We do this so that
                    # we only count the most specific req when comparing incoming versions.
                    try:
                        req = reduce(merge_requirements, ws_reqs)
                    except CannotMergeError:
                        log.warn("This virtualenv is inconsistant - %s is installed but there are"
                                 "un-mergeable requirements:" % dist)
                        [log.warn("  %s (from %s)" % (i, i._dist)) for i in ws_reqs]
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
            #       The second invocation should store the full requirement here,
            #       so that the user needs to override their own req manually.
            req = pkg_resources.Requirement.parse(dist.project_name)

        if not req:
            log.warn("Trimming dist from baseline ws as it's inconsistant: %r" % dist)
            remove_from_ws(ws, dist)
        else:
            #log.debug("   best is now (%s): %r" % (req, dist))
            best[req.key] = (dist, req)
            req._chosen_dist = dist
            baseline_reqs[req.key] = req
            req._child_reqs = []

    # Now fill out the requirements graph.
    # We can do this easily as at this point there is exactly one req for each dist.
    for dist, req in best.values():
        req_graph.add_node(req)
        [req_graph.add_edge(req, baseline_reqs[r.key])
         for r in dist.requires()
         if r.key in baseline_reqs]
        #req._child_reqs = [baseline_reqs[r.key] for r in dist.requires()  \
        #                   if r.key in baseline_reqs]

    return best


def get_all_upstream(graph, req):
    """ Return all upstream requirements in a given graph
    """
    from networkx import algorithms
    # dfs_successors returns a dict representing the edges its found. Flatten it.
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


def get_downstream_difference(graph, upstream_node, downstream_node):
    """ Return the difference between the upstream and downstream
        sets of two nodes. Used to find if there are more than
        one distinct downstream nodes, eg:
             A       B    A depends on D, B depends on C and D
              \     /
               \   C      C only has one downstream parent, but
                \ /       D has both A and B downstream.
                 D
    """
    # XXX this doesn't work yet, I expect it is failing on circular graphs
    down_to_up = get_all_upstream(graph, downstream_node)
    down_to_up = down_to_up.difference(get_all_upstream(graph, upstream_node))
    down_to_up.add(upstream_node)

    up_to_down = get_all_downstream(graph, upstream_node)
    up_to_down = up_to_down.difference(get_all_downstream(graph, downstream_node))
    up_to_down.add(downstream_node)
    return down_to_up.difference(up_to_down)
