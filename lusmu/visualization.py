from __future__ import print_function, unicode_literals

from lusmu.core import Node
import subprocess


def collect_nodes(collected_nodes, *args):
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


def graphviz_lines(nodes):
    all_nodes = set()
    collect_nodes(all_nodes, *nodes)
    all_nodes = sorted(all_nodes)
    input_nodes = [n for n in all_nodes if n.name.startswith('Input:')]

    yield 'digraph gr {'
    yield '  rankdir = LR;'
    yield '  { rank = source;'
    for node in input_nodes:
        yield '    n{};'.format(id(node))
    yield '  }'
    for node in all_nodes:
        yield ('  n{node} [label="{name}"];'
               .format(node=id(node), name=node.name.replace(':', r'\n')))
        yield '  edge [color=blue];'
        for other in node._dependents:
            yield ('  n{node} -> n{other} [label="data"];'
                   .format(node=id(node), other=id(other)))
        yield '  edge [color=red];'
        if isinstance(node, Node):
            for other in node._iterate_inputs():
                yield ('  n{node} -> n{other} [label="input"];'
                       .format(node=id(node), other=id(other)))
    yield '}'


def visualize_graph(nodes, filename):
    graphviz = subprocess.Popen(['dot', '-Tpng', '-o', filename],
                                stdin=subprocess.PIPE)
    source = '\n'.join(graphviz_lines(nodes))
    graphviz.communicate(source.encode('utf-8'))
    return source
