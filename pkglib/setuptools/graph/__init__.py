"""
Dependency graph visualization methods
"""
import os
import shutil
import time
from distutils import log
import tempfile
import webbrowser
import string
import operator

from pkg_resources import working_set

from pkglib.cmdline import run
from pkglib.manage import chdir, is_inhouse_package
from pkglib import CONFIG


def get_spec(specs):
    """ Text repr of Requirement.specs """
    return ' '.join("%s %s" % (i[0].replace('>', '\>'),
                               i[1].replace('>', '\>')) for i in specs)


def get_dot_node(req):
    """ Get a pydot node object from a networkx node """
    import pydot
    fill_colour = "#cccccc"
    shape = "box"
    if is_inhouse_package(req.project_name):
        fill_colour = "green"
    return pydot.Node(' '.join((str(req.project_name), req._chosen_dist.version)),
                      style="filled",
                      fillcolor=fill_colour,
                      shape=shape)


def get_dot_edge(edge, nodes):
    """ Get a pydot edge object from a networkx edge """
    import pydot
    # PyDot's lame argument handling means I can't pass in label=None
    if edge[1].specs:
        return pydot.Edge(nodes[edge[0]],
                          nodes[edge[1]],
                          label=get_spec(edge[1].specs))
    return pydot.Edge(nodes[edge[0]], nodes[edge[1]])


def draw_networkx_with_pydot(nx_graph, include_third_party=False, outfile=None):
    """ Draws a networkx graph using PyDot.
    """
    log.info("")
    import pydot
    dot_graph = pydot.Dot(graph_type='digraph', suppress_disconnected=False)
    dot_nodes = {}
    for nx_node in nx_graph.nodes_iter():
        if not include_third_party and not is_inhouse_package(nx_node.project_name):
            continue
        dot_node = get_dot_node(nx_node)
        dot_nodes[nx_node] = dot_node
        dot_graph.add_node(dot_node)

    for edge in nx_graph.edges_iter():
        if edge[0] not in dot_nodes or edge[1] not in dot_nodes:
            continue
        dot_graph.add_edge(get_dot_edge(edge, dot_nodes))

    if not outfile:
        tmpdir = tempfile.mkdtemp()
        outfile = os.path.abspath(os.path.join(tmpdir, 'graph.png'))
    # TODO: make neato work for nicer layouts
    #dot_graph.write_png(outfile, prog='neato')
    dot_graph.write_png(outfile)
    webbrowser.open('file://%s' % outfile)
    time.sleep(5)
    if not outfile:
        shutil.rmtree(tmpdir)


def draw_networkx_with_d3(nx_graph, include_third_party=False, outfile=None):
    """ Draws a networkx graph using d3.
    """
    from path import path
    tmpl = string.Template((path(__file__).parent / 'd3' / 'fbl.html').text())

    nodes = {}
    edges = []

    i = 0
    for req in nx_graph.nodes_iter():
        if not include_third_party and not is_inhouse_package(req.project_name):
            continue
        #print "Node %d: %s" % (i, req.project_name)
        nodes[req.key] = (i, req.project_name)
        i += 1

    for edge in nx_graph.edges_iter():
        if edge[0].key not in nodes or edge[1].key not in nodes:
            continue
        #print "edge: %s -> %s" % (edge[0].key, edge[1].key)
        #print '{source : %d, target: %d, weight: 1}' % (nodes[edge[0].key][0], nodes[edge[1].key][0])
        edges.append('{source : %d, target: %d, weight: 0.5}' % (nodes[edge[0].key][0], nodes[edge[1].key][0]))

    nodes = ',\n'.join(['{label: "%s"}' % i[1] for i in sorted(nodes.values(), key=operator.itemgetter(0))])
    edges = ',\n'.join(edges)

    if not outfile:
        tmpdir = path(tempfile.mkdtemp())
        outfile = tmpdir / 'graph.html'
    else:
        outfile = path(outfile)
    outfile.write_text(tmpl.safe_substitute(nodes=nodes, links=edges))
    webbrowser.open('file://%s' % outfile)
    time.sleep(5)
    if not outfile:
        shutil.rmtree(tmpdir)


def get_module_node(all_modules, name):
    dist = all_modules[name.lower()]
    return "[ %s (%s) ]" % (dist.project_name, dist.version)


def get_req_node(all_modules, dist_name, req):
    return "%s -- %s --> %s" % (
        get_module_node(all_modules, dist_name),
        get_spec(req.specs),
        get_module_node(all_modules, req.project_name))


def draw_graph(inclusions=None, exclusions=None, renderer='boxart', outfile=None):
    """
    Draw a graph of our current working set.

    Parameters
    ----------
    inclusions : `list`
        Include only these packages, empty or None denotes all.
    exclusions : `list`
        Exclude these packages
    renderer : `str`
        Renderer mode, one of `ascii`, `boxart` or `graphviz`
    outfile : `str`
        File to save to for graphviz mode
    """
    inc = [i.lower() for i in inclusions] if inclusions else []
    exc = [i.lower() for i in exclusions] if exclusions else []
    # This initial entry helps with the layout of the graph
    # See http://bloodgate.com/perl/graph/manual/hinting.html
    entries = [
        'graph { flow: south; }',
    ]
    all_modules = dict(list((i.project_name.lower(), i) for i in working_set))

    def included(name):
        if inclusions and name.lower() not in inc:
            return False
        if exclusions and name.lower() in exc:
            return False
        return True

    for dist in working_set:
        if not included(dist.project_name):
            continue
        entries.append(get_module_node(all_modules, dist.project_name))
        [entries.append(get_req_node(all_modules, dist.project_name, r))
         for r in dist.requires()
         if included(r.project_name)]

    if renderer == "boxart":
        log.info("Using UTF-8 boxart: if this looks strange set your terminal chacter encoding to "
                 "UTF-8 or use --ascii")
    run_graph_easy(entries, renderer, outfile)


def run_graph_easy(entries, renderer, outfile=None):
    """ Given the path edge entries, run the graphing tools and produce the output.

        Parameters
        ----------
        entries :    `list`
            Path edges
        renderer :   `str`
            One of 'ascii', 'boxart' or 'graphviz'
        outfile :   `str`
            File to save to, only for graphviz. If None, it will delete the generated file.
    """
    from path import path
    if renderer == 'graphviz' and not os.getenv('DISPLAY'):
        log.info("No DISPLAY set, using ascii renderer")
        renderer = 'ascii'

    instream = '\n'.join(entries)
    if os.path.isfile(CONFIG.graph_easy / 'bin' / 'graph-easy'):
        with chdir(CONFIG.graph_easy / 'lib'):
            if renderer == 'graphviz':
                delete = False
                if not outfile:
                    tmpdir = path(tempfile.mkdtemp())
                    outfile = tmpdir / 'depgraph.png'
                    delete = True
                outfile = path(outfile)
                outfile = outfile.abspath()

                run(['-c', '../bin/graph-easy --as=%s | /usr/bin/dot -Tpng -o %s' % (renderer, outfile)],
                    capture_stdout=False, stdin=instream, shell=True)
                if not outfile.isfile:
                    log.error("Failed to create image file.")
                    return
                webbrowser.open('file://%s' % outfile)
                if delete:
                    time.sleep(5)
                    shutil.rmtree(tmpdir)
                else:
                    log.info("Created graph at %s" % outfile)
            else:
                run(['../bin/graph-easy', '--as=%s' % renderer], capture_stdout=False, stdin=instream)
        return
    log.warn("Can't find graphing tool at %s" % CONFIG.graph_easy)
