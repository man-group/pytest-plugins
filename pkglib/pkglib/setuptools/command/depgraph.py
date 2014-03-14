from distutils.errors import DistutilsOptionError
from setuptools import Command

from pkg_resources import safe_name, working_set, parse_requirements

from pkglib.setuptools import dependency, graph

from .base import CommandMixin, fetch_build_eggs


class depgraph(Command, CommandMixin):
    """ Print a dependency graph of this package """
    description = "Display dependency graphs."
    command_consumes_arguments = True

    user_options = [
        ('third-party', 't', 'Include third-party packages'),
        ('everything', 'e', 'Include all installed packages'),
        ('ascii', 'A', 'Use ascii renderer'),
        ('boxart', 'b', 'Use UTF-8 boxart renderer'),
        ('graphviz', 'g', 'Use GraphViz renderer'),
        ('d3', 'd', 'Use D3 renderer'),
        ('pydot', 'p', 'Use PyDot renderer'),
        ('out=', 'o', 'Save file to given location'),
        ('exclude=', 'x', 'Exclude these packages, comma-separated'),
        ('what-requires=', 'r',
         'Shows what packages require the given package name'),
    ]
    boolean_options = [
        'everything',
        'third_party',
        'ascii',
        'boxart',
        'd3',
        'pydot',
        'graphviz',
    ]

    def initialize_options(self):
        self.args = []
        self.third_party = False
        self.everything = False
        self.ascii = False
        self.boxart = False
        self.d3 = False
        self.graphviz = False
        self.pydot = True
        self.out = None
        self.renderer = 'pydot'
        self.exclude = []
        self.what_requires = None
        self.what_provides = None

    def finalize_options(self):
        if self.ascii:
            self.renderer = 'ascii'
        elif self.boxart:
            self.renderer = 'boxart'
        elif self.d3:
            self.renderer = 'd3'
        elif self.graphviz:
            self.renderer = 'graphviz'
        elif self.pydot:
            self.renderer = 'pydot'
        if self.exclude:
            self.exclude = self.exclude.split(',')

    def _resolve_all_packages(self):
        all_packages = dependency.all_packages(exclusions=self.exclude,
                                               include_third_party=self.third_party,
                                               exclude_pinned=False)

        if self.distribution.get_name() == 'UNKNOWN' and not self.args:
            # Pick any package and set the 'everything' flag if nothing was
            # specified
            pkg = all_packages.keys()[0]
            self.everything = True
            self.args = [pkg]
            if 'UNKNOWN' in all_packages:
                del all_packages['UNKNOWN']

        return all_packages

    def _resolve_roots(self, all_packages):
        roots = []
        if self.args:
            roots = [safe_name(i) for i in self.args]
            for i in roots:
                if not i in all_packages.keys():
                    raise DistutilsOptionError("Unknown package: %s" % i)

        if not roots:
            roots = [self.distribution.get_name()]

        return roots

    def _render_ascii(self, roots, all_packages):
        tgts = dependency.get_targets(roots, all_packages, everything=self.everything)
        graph.draw_graph(inclusions=tgts, renderer=self.renderer, outfile=self.out)

    def _render_digraph(self, nx_graph):
        if self.renderer == 'd3':
            graph.draw_networkx_with_d3(nx_graph, self.third_party, self.out)
        elif self.renderer == 'pydot':
            fetch_build_eggs(['pydot'], dist=self.distribution)
            graph.draw_networkx_with_pydot(nx_graph, self.third_party, self.out)

    def _filter_nodes_leading_to(self, nx_graph, target_node):
        # XXX do this properly
        class d:
            version = ""
        guilty_nodes = set()
        resolved = set()

        for req in parse_requirements(target_node):
            # fudge _chosen_dist, couldn't work out how to resolve it properly
            req._chosen_dist = d
            guilty_nodes.add(req)
            resolved.add(req)
            guilty_nodes.update(nx_graph.predecessors_iter(req))

        while len(guilty_nodes) != len(resolved):
            for n in [gn for gn in guilty_nodes if gn not in resolved]:
                resolved.add(n)
                guilty_nodes.update(nx_graph.predecessors_iter(n))

        return nx_graph.subgraph(guilty_nodes)

    def run(self):
        if not self.distribution.get_name() == 'UNKNOWN':
            self.run_command('egg_info')
        self.banner("Dependency Graph: note: includes only installed packages")

        all_packages = self._resolve_all_packages()
        roots = self._resolve_roots(all_packages)

        self.banner("Rendering using %s" % self.renderer)

        if self.renderer in ['ascii', 'graphviz']:
            # TODO: use nx digraph as below, retire get_targets
            self._render_ascii(roots, all_packages)
        else:
            import networkx
            g = networkx.DiGraph()
            dependency.get_graph_from_ws(working_set, g)

            if self.what_requires is not None:
                g = self._filter_nodes_leading_to(g, self.what_requires)

            self._render_digraph(g)
