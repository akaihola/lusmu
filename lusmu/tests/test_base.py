"""Unit tests for lusmu.base"""

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
    """Test case for basic functionality of the Node class"""

    def test_missing_evaluate(self):
        """The Node class must be subclassed, it doesn't work by itself"""
        with self.assertRaises(NotImplementedError):
            IncompleteNode('name').get_value()

    def test_name(self):
        """A node uses its name in its string representation"""
        self.assertEqual('<ConstantNode node: DIRTY>',
                         repr(ConstantNode('node')))

    def test_default_name(self):
        """A default name is generated for a node if the name is omitted"""
        class AutoNamedNode(Node):
            """Node subclass for testing automatic names"""

        self.assertEqual('AutoNamedNode-1', AutoNamedNode().name)

    def test_default_name_with_action(self):
        """The default name of a node includes action func_name if available"""
        class ActionNamedNode(Node):
            """Node subclass for testing action names in automatic names"""

        def my_action(arg):
            """Dummy example action"""

        node = ActionNamedNode(action=my_action)
        self.assertEqual('ActionNamedNode-my_action-1', node.name)

    def test_node_classes_have_separate_counters(self):
        """All Node classes have separate counters for auto-generated names"""
        class CounterNodeA(Node):
            """Node subclass for testing"""

        self.assertEqual('CounterNodeA-1', CounterNodeA().name)

        class CounterNodeB(Node):
            """Node subclass for testing"""

        class CounterNodeC(Node):
            """Node subclass for testing"""

        self.assertEqual('CounterNodeB-1', CounterNodeB().name)
        self.assertEqual('CounterNodeC-1', CounterNodeC().name)
        self.assertEqual('CounterNodeC-2', CounterNodeC().name)

    def test_initial_inputs(self):
        """Inputs of a node can be set up in the constructor"""
        root = ConstantNode('root')
        branch = ConstantNode('branch')
        leaf = ConstantNode('node', inputs=([root], {'branch': branch}))
        self.assertEqual({leaf}, root._dependents)
        self.assertEqual({leaf}, branch._dependents)
        self.assertEqual((root,), leaf._positional_inputs)
        self.assertEqual({'branch': branch}, leaf._keyword_inputs)

    def test_changing_inputs_disconnects_dependencies(self):
        """Old dependencies are disconnected when changing inputs of a Node"""
        root1 = ConstantNode('root1')
        leaf = ConstantNode('leaf', inputs=([root1], {}))
        self.assertEqual({leaf}, root1._dependents)
        root2 = ConstantNode('root2')
        root3 = ConstantNode('root3')
        leaf.set_inputs(root2, foo=root3)
        self.assertEqual(set(), root1._dependents)
        self.assertEqual({leaf}, root2._dependents)
        self.assertEqual({leaf}, root3._dependents)

    def test_initial_value(self):
        """The initial value of a Node can be set in the constructor"""
        node = Node(value=5)
        self.assertEqual(5, node._value)

    def test_value_property_setter(self):
        """The value of a Node can be set with the .value property"""
        root = Node()
        leaf = Node(action=lambda value: value, inputs=Node.inputs(root))
        root.value = 5
        self.assertEqual(5, leaf.get_value())

    def test_value_property_getter(self):
        """The value of a Node can be set with the .value property"""
        root = Node(value=5)
        leaf = Node(action=lambda value: value, inputs=Node.inputs(root))
        self.assertEqual(5, leaf.value)


class NodeDependentTestCase(TestCase):
    """Test case for triggered dependent Nodes"""

    def setUp(self):
        self.root = ConstantNode('root')
        self.dependent = ConstantNode('dependent', triggered=False)
        self.root._connect(self.dependent)
        self.triggered = ConstantNode('triggered', triggered=True)
        self.root._connect(self.triggered)

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
        triggered_nodes = self.root._get_triggered_dependents()
        self.assertEqual({self.triggered}, triggered_nodes)

    def test_get_deep_triggered_dependents(self):
        """Setting a value to a dirty Node triggers dependents tree"""
        child1 = ConstantNode('child1', triggered=True)
        child2 = ConstantNode('child2', triggered=True)
        self.triggered._connect(child1)
        self.triggered._connect(child2)
        triggered_nodes = self.root._get_triggered_dependents()
        self.assertEqual({self.triggered, child1, child2}, triggered_nodes)


class CountingNode(ConstantNode):
    """Node class which counts calls to _get_triggered_dependents()"""

    def __init__(self, *args, **kwargs):
        super(CountingNode, self).__init__(*args, **kwargs)
        self.call_count = 0

    def _get_triggered_dependents(self, *args, **kwargs):
        self.call_count += 1
        return super(CountingNode, self)._get_triggered_dependents(*args,
                                                                   **kwargs)


class TriggeredCacheTestCase(TestCase):
    """Test case for the cache of triggered nodes"""

    def setUp(self):
        self.root = CountingNode('root')
        self.branch = CountingNode('branch', triggered=True)
        self.leaf1 = CountingNode('leaf1', triggered=True)
        self.leaf2 = CountingNode('leaf2', triggered=True)
        self.root._connect(self.branch)
        self.branch._connect(self.leaf1)
        self.branch._connect(self.leaf2)

    def test_cache_content(self):
        """Triggered dependents are cached for each node"""
        self.root._get_triggered_dependents()
        self.assertEqual({self.root: {self.branch, self.leaf1, self.leaf2}},
                         _triggered_cache)

    def test_connect_clears_cache(self):
        """Connecting nodes invalidates the triggered nodes cache"""
        self.root._get_triggered_dependents()
        self.assertEqual({self.root: {self.branch, self.leaf1, self.leaf2}},
                         _triggered_cache)
        self.root._connect(CountingNode('leaf3'))
        self.assertEqual({}, _triggered_cache)

    def test_get_triggered_dependents(self):
        """_get_triggered_dependents() isn't called again for cached nodes"""
        self.root._get_triggered_dependents()
        self.assertEqual(1, self.root.call_count)
        self.assertEqual(1, self.branch.call_count)
        self.assertEqual(1, self.leaf1.call_count)
        self.assertEqual(1, self.leaf2.call_count)
        self.root._get_triggered_dependents()
        self.assertEqual(2, self.root.call_count)
        self.assertEqual(1, self.branch.call_count)
        self.assertEqual(1, self.leaf1.call_count)
        self.assertEqual(1, self.leaf2.call_count)


class NodeSetValueTestCase(TestCase):
    """Test case for Node.set_value()"""

    def test_set_value(self):
        """A value set to a dirty Node is stored in the object"""
        node = Node('name')
        node.set_value(0)
        self.assertEqual(0, node._value)


class UpdateNodesTestCase(TestCase):
    """Test case for update_nodes*() methods"""

    def setUp(self):
        self.root = CountingNode('root')
        self.branch1 = CountingNode('branch1', triggered=True)
        self.branch2 = CountingNode('branch2', triggered=True)
        self.leaf1 = CountingNode('leaf1', triggered=True)
        self.leaf2 = CountingNode('leaf2', triggered=True)
        self.leaf3 = CountingNode('leaf3', triggered=True)
        self.leaf4 = CountingNode('leaf4', triggered=True)
        self.root._connect(self.branch1)
        self.root._connect(self.branch2)
        self.branch1._connect(self.leaf1)
        self.branch1._connect(self.leaf2)
        self.branch2._connect(self.leaf3)
        self.leaf3._connect(self.leaf4)

    def test_only_leafs_triggered_1(self):
        """Updating a Node only triggers its descendents"""
        triggered = update_nodes_get_triggered([(self.branch1, 2)])
        self.assertEqual({self.leaf1, self.leaf2}, triggered)

    def test_only_leafs_triggered_2(self):
        """Updating a Node only triggers its descendents"""
        triggered = update_nodes_get_triggered([(self.branch2, 2)])
        self.assertEqual({self.leaf3, self.leaf4}, triggered)


class HomeAutomationTestCase(TestCase):
    """Test case illustrating a fictitious home automation use case"""

    def test_home_automation(self):
        """A simple example in the home automation domain"""
        brightness_1 = Node()
        brightness_2 = Node()
        brightness_sum = Node(action=lambda *args: sum(args),
                              inputs=Node.inputs(brightness_1, brightness_2))

        def inverse(value):
            """Return the inverse of a value in the range 0..510"""
            return 510 - value

        brightness_inverse = Node(action=inverse,
                                  inputs=Node.inputs(brightness_sum))

        lamp_power_changes = []

        def set_lamp_power(value):
            """Log changes to lamp power"""
            lamp_power_changes.append(value)

        _lamp_power = Node(action=set_lamp_power,
                           inputs=Node.inputs(brightness_inverse),
                           triggered=True)

        update_nodes_get_triggered([(brightness_1, 20),
                                    (brightness_2, 40)])

        self.assertEqual([450], lamp_power_changes)

        update_nodes_get_triggered([(brightness_1, 20),
                                    (brightness_2, 40)])

        self.assertEqual([450], lamp_power_changes)

        update_nodes_get_triggered([(brightness_1, 24),
                                    (brightness_2, 40)])

        self.assertEqual([450, 446], lamp_power_changes)
