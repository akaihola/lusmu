"""Unit tests for lusmu.visualization.

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

from lusmu.core import Node, Input
from lusmu.visualization import collect_nodes


def test_collect_nodes_huge_number_of_inputs():
    """Assert that collect_nodes accepts a large number of input nodes

    Test that the recursion in :func:`collect_nodes` does not break with many
    input nodes.

    """
    nodes = []
    collected_nodes = set()

    for val in xrange(1000):
        nodes.append(Input('input%d' % val))
    nodes.append(Node(inputs=Node.inputs(*nodes)))

    collect_nodes(collected_nodes, nodes[-1])