# pylint: disable=W0212
#         Access to a protected member of a client class

from unittest import TestCase
from lusmu.base import (DIRTY,
                        Node,
                        update_nodes_get_triggered,
                        _triggered_cache)


class IncompleteNode(Node):
    """A Node subclass which doesn't implement ._evaluate()"""
    pass


class ConstantNode(Node):
    """A Node subclass which always evaluates to the value 1"""
    def _evaluate(self):
        return 1


class NodeTestCase(TestCase):
    def test_missing_evaluate(self):
        """The Node class must be subclassed, it doesn't work by itself"""
        with self.assertRaises(NotImplementedError):
            IncompleteNode('name').get_value()

    def test_name(self):
        """A node uses its name in its string representation"""
        self.assertEqual('<ConstantNode node: DIRTY>',
                         repr(ConstantNode('node')))

    def test_initial_inputs(self):
        """Inputs of a node can be set up in the constructor"""
        root = ConstantNode('root')
        branch = ConstantNode('branch')
        leaf = ConstantNode('node', inputs=([root], {'branch': branch}))
        self.assertEqual({leaf}, root._dependents)
        self.assertEqual({leaf}, branch._dependents)
        self.assertEqual((root,), leaf._positional_inputs)
        self.assertEqual({'branch': branch}, leaf._keyword_inputs)

    def test_changing_inputs_disconnects_dependents(self):
        root1 = ConstantNode('root1')
        leaf = ConstantNode('leaf', inputs=([root1], {}))
        self.assertEqual({leaf}, root1._dependents)
        root2 = ConstantNode('root2')
        root3 = ConstantNode('root3')
        leaf.set_inputs(root2, foo=root3)
        self.assertEqual(set(), root1._dependents)
        self.assertEqual({leaf}, root2._dependents)
        self.assertEqual({leaf}, root3._dependents)


class NodeDependentTestCase(TestCase):
    def setUp(self):
        self.root = ConstantNode('root')
        self.dependent = ConstantNode('dependent', triggered=False)
        self.root.connect(self.dependent)
        self.triggered = ConstantNode('triggered', triggered=True)
        self.root.connect(self.triggered)

    def test_keep_dirty(self):
        """Setting a dirty Node as dirty doesn't trigger dependents"""
        triggered_nodes = self.root.set_value(DIRTY)
        self.assertEqual(set(), triggered_nodes)

    def test_set_value_triggers_dependents(self):
        """Setting a value to a dirty Node triggers dependents"""
        triggered_nodes = self.root.set_value(0)
        self.assertEqual({self.triggered}, triggered_nodes)

    def test_get_triggered_dependents(self):
        """Setting a value to a dirty Node triggers dependents"""
        triggered_nodes = self.root.get_triggered_dependents()
        self.assertEqual({self.triggered}, triggered_nodes)

    def test_get_deep_triggered_dependents(self):
        """Setting a value to a dirty Node triggers dependents tree"""
        child1 = ConstantNode('child1', triggered=True)
        child2 = ConstantNode('child2', triggered=True)
        self.triggered.connect(child1)
        self.triggered.connect(child2)
        triggered_nodes = self.root.get_triggered_dependents()
        self.assertEqual({self.triggered, child1, child2}, triggered_nodes)


class CountingNode(ConstantNode):
    def __init__(self, *args, **kwargs):
        super(CountingNode, self).__init__(*args, **kwargs)
        self.call_count = 0

    def get_triggered_dependents(self, *args, **kwargs):
        self.call_count += 1
        return super(CountingNode, self).get_triggered_dependents(*args,
                                                                  **kwargs)


class TriggeredCacheTestCase(TestCase):
    def setUp(self):
        self.root = CountingNode('root')
        self.branch = CountingNode('branch', triggered=True)
        self.leaf1 = CountingNode('leaf1', triggered=True)
        self.leaf2 = CountingNode('leaf2', triggered=True)
        self.root.connect(self.branch)
        self.branch.connect(self.leaf1)
        self.branch.connect(self.leaf2)

    def test_cache_content(self):
        """Triggered dependents are cached for each node"""
        self.root.get_triggered_dependents()
        self.assertEqual({self.root: {self.branch, self.leaf1, self.leaf2}},
                         _triggered_cache)

    def test_connect_clears_cache(self):
        """Connecting nodes invalidates the triggered nodes cache"""
        self.root.get_triggered_dependents()
        self.assertEqual({self.root: {self.branch, self.leaf1, self.leaf2}},
                         _triggered_cache)
        self.root.connect(CountingNode('leaf3'))
        self.assertEqual({}, _triggered_cache)

    def test_get_triggered_dependents(self):
        """get_triggered_dependents() isn't called again for cached nodes"""
        self.root.get_triggered_dependents()
        self.assertEqual(1, self.root.call_count)
        self.assertEqual(1, self.branch.call_count)
        self.assertEqual(1, self.leaf1.call_count)
        self.assertEqual(1, self.leaf2.call_count)
        self.root.get_triggered_dependents()
        self.assertEqual(2, self.root.call_count)
        self.assertEqual(1, self.branch.call_count)
        self.assertEqual(1, self.leaf1.call_count)
        self.assertEqual(1, self.leaf2.call_count)


class NodeSetValueTestCase(TestCase):
    def test_set_value(self):
        """A value set to a dirty Node is stored in the object"""
        node = Node('name')
        node.set_value(0)
        self.assertEqual(0, node._value)


class UpdateNodesTestCase(TestCase):
    def setUp(self):
        self.root = CountingNode('root')
        self.branch1 = CountingNode('branch1', triggered=True)
        self.branch2 = CountingNode('branch2', triggered=True)
        self.leaf1 = CountingNode('leaf1', triggered=True)
        self.leaf2 = CountingNode('leaf2', triggered=True)
        self.leaf3 = CountingNode('leaf3', triggered=True)
        self.leaf4 = CountingNode('leaf4', triggered=True)
        self.root.connect(self.branch1)
        self.root.connect(self.branch2)
        self.branch1.connect(self.leaf1)
        self.branch1.connect(self.leaf2)
        self.branch2.connect(self.leaf3)
        self.leaf3.connect(self.leaf4)

    def test_only_leafs_triggered_1(self):
        """Updating a Node only triggers its descendents"""
        triggered = update_nodes_get_triggered([(self.branch1, 2)])
        self.assertEqual({self.leaf1, self.leaf2}, triggered)

    def test_only_leafs_triggered_2(self):
        """Updating a Node only triggers its descendents"""
        triggered = update_nodes_get_triggered([(self.branch2, 2)])
        self.assertEqual({self.leaf3, self.leaf4}, triggered)
