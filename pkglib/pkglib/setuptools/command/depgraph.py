from distutils.errors import DistutilsOptionError
from distutils import log

from setuptools import Command
from pkg_resources import safe_name, working_set

from pkglib.setuptools import dependency, graph

from base import CommandMixin


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
        ('requirements', 'r',
         'Show requirements graph instead of distributions. Currently only '
         'supported by pydot.'),
        ('out=', 'o', 'Save file to given location'),
        ('exclude=', 'x', 'Exclude these packages, comma-separated'),
    ]
    boolean_options = [
        'everything',
        'third_party',
        'ascii',
        'boxart',
        'd3',
        'pydot',
        'graphviz',
        'requirements',
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
        self.requirements = False

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
        if self.everything:
            self.third_party = True

    def run(self):
        if not self.distribution.get_name() == 'UNKNOWN':
            self.run_command('egg_info')
        self.banner("Dependency Graph: note - includes only installed "
                    "packages")

        all_packages = dependency.all_packages(
                           exclusions=self.exclude,
                           include_third_party=self.third_party,
                           exclude_pinned=False)
        if not all_packages:
            log.info("No matching packages to render")
            return


        if self.distribution.get_name() == 'UNKNOWN' and not self.args:
            # Pick any package and set the 'everything' flag if nothing was 
            # specified
            pkg = all_packages.keys()[0]
            self.everything = True
            self.args = [pkg]
            if 'UNKNOWN' in all_packages:
                del all_packages['UNKNOWN']

        roots = []
        if self.args:
            roots = [safe_name(i) for i in self.args]
            for i in roots:
                if not i in all_packages.keys():
                    raise DistutilsOptionError("Unknown package: %s" % i)

        if not roots:
            roots = [self.distribution.get_name()]

        self.banner("Rendering using %s" % self.renderer)

        if self.renderer in ['ascii', 'graphviz']:
            # TODO: use nx digraph as below, retire get_targets
            src, eggs = dependency.get_targets(roots, all_packages,
                                               everything=self.everything,
                                               immediate_deps=True,
                                               follow_all=True,
                                               include_eggs=True,
                                               include_source=True,)

            graph.draw_graph(inclusions=src + eggs, renderer=self.renderer,
                             outfile=self.out)

        else:
            nx_graph, _ = dependency.get_graph_from_ws(working_set)

            if self.renderer == 'd3':
                graph.draw_networkx_with_d3(nx_graph, self.third_party,
                                            self.out)
            elif self.renderer == 'pydot':
                self.fetch_build_eggs(['pydot'])
                graph.draw_networkx_with_pydot(nx_graph, self.third_party,
                                               self.out, self.requirements)
