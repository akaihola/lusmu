"""Tools for visualizing a lusmu graph"""

# pylint: disable=W0212
#         Allow access to protected members of client classes
# pylint: disable=W0142
#         Allow * and ** magic

from __future__ import print_function, unicode_literals

from lusmu.core import Input, Node
import subprocess


def collect_nodes(collected_nodes, *args):
    """Collect all nodes belonging to the same graph

    Walks dependent Nodes and inputs recursively.

    """
    if not args:
        return
    node = args[0]
    if node in collected_nodes:
        return
    rest = args[1:]
    collect_nodes(collected_nodes, *rest)
    collected_nodes.add(node)
    collect_nodes(collected_nodes, *node._dependents)
    if isinstance(node, Node):
        collect_nodes(collected_nodes, *node._iterate_inputs())


def graphviz_lines(nodes, node_filter):
    """Generate source lines for a Graphviz graph definition"""
    all_nodes = set()
    collect_nodes(all_nodes, *nodes)
    if node_filter:
        all_nodes = [n for n in all_nodes if node_filter(n)]
    all_nodes = sorted(all_nodes, key=id)
    input_nodes = [n for n in all_nodes if isinstance(n, Input)]

    yield 'digraph gr {'
    yield '  rankdir = LR;'
    yield '  { rank = source;'
    for node in input_nodes:
        yield '    n{};'.format(id(node))
    yield '  }'
    for node in all_nodes:
        yield ('  n{node} [label="[{name}]{action}"];'
               .format(node=id(node),
                       name=node.name.replace(':', r'\n'),
                       action='\\n\\n{}'.format(node._action.name)
                       if isinstance(node, Node)
                       else ''))
        yield '  edge [color=blue];'
        for other in node._dependents:
            if other in all_nodes:
                yield ('  n{node} -> n{other};'
                       .format(node=id(node), other=id(other)))
    yield '}'


def visualize_graph(nodes, filename, node_filter=lambda node: True):
    """Saves a visualization of given nodes in a PNG file"""
    graphviz = subprocess.Popen(['dot', '-Tpng', '-o', filename],
                                stdin=subprocess.PIPE)
    source = '\n'.join(graphviz_lines(nodes, node_filter))
    graphviz.communicate(source.encode('utf-8'))
    return source
