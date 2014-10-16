"""Unit tests for lusmu.core

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

# pylint: disable=W0212
#         Access to a protected member of a client class
# pylint: disable=C0103
#         Allow long method names
# pylint: disable=R0904
#         Allow lots of public methods

import gc
from unittest import TestCase
from nose.tools import assert_raises
import numpy as np
from lusmu.core import (OpNode,
                        NO_DATA,
                        SrcNode,
                        update_source_nodes_get_triggered,
                        _TRIGGERED_CACHE)
from mock import patch
import weakref


class IncompleteNode(OpNode):
    """An operation node subclass which doesn't implement ._evaluate()"""
    pass


class ConstantNode(OpNode):
    """An operation node subclass which always evaluates to the value 1"""
    def _evaluate(self):
        return 1


class OpNodeTestCase(TestCase):
    """Test case for basic functionality of the OpNode class"""

    def test_missing_evaluate(self):
        """The OpNode class must be subclassed, it doesn't work by itself"""
        with self.assertRaises(NotImplementedError):
            IncompleteNode('name').get_data()

    def test_name(self):
        """A node uses its name in its string representation"""
        self.assertEqual('<ConstantNode node: NO_DATA>',
                         repr(ConstantNode('node')))

    def test_default_name(self):
        """A default name is generated for a node if the name is omitted"""
        class AutoNamedSrcNode(SrcNode):
            """OpNode subclass for testing automatic names"""

        self.assertEqual('AutoNamedSrcNode-1', AutoNamedSrcNode().name)

    def test_default_name_with_operation(self):
        """The default name of a node includes operation func_name if available"""
        class NamedNode(OpNode):
            """OpNode subclass for testing operation names in automatic names"""

        def my_operation(_arg):
            """Dummy example operation"""

        node = NamedNode(op=my_operation)
        self.assertEqual('NamedNode-my_operation-1', node.name)

    def test_node_classes_have_separate_counters(self):
        """All node classes have separate counters for auto-generated names"""
        class CounterNodeA(SrcNode):
            """Node subclass for testing"""

        self.assertEqual('CounterNodeA-1', CounterNodeA().name)

        class CounterNodeB(SrcNode):
            """Node subclass for testing"""

        class CounterNodeC(OpNode):
            """Node subclass for testing"""

        self.assertEqual('CounterNodeB-1', CounterNodeB().name)
        self.assertEqual('CounterNodeC-1', CounterNodeC().name)
        self.assertEqual('CounterNodeC-2', CounterNodeC().name)

    def test_initial_inputs(self):
        """Nodes can be connected to input ports in the constructor"""
        root = ConstantNode('root')
        branch = ConstantNode('branch')
        leaf = ConstantNode('node', inputs=([root], {'branch': branch}))
        self.assertEqual({leaf}, root._dependents)
        self.assertEqual({leaf}, branch._dependents)
        self.assertEqual((root,), leaf._positional_inputs)
        self.assertEqual({'branch': branch}, leaf._keyword_inputs)

    def test_changing_inputs_disconnects_dependencies(self):
        """Old dependents are disconnected when changing inputs of a node"""
        root1 = ConstantNode('root1')
        leaf = ConstantNode('leaf', inputs=([root1], {}))
        self.assertEqual({leaf}, root1._dependents)
        root2 = ConstantNode('root2')
        root3 = ConstantNode('root3')
        leaf.set_inputs(root2, foo=root3)
        self.assertEqual(set(), root1._dependents)
        self.assertEqual({leaf}, root2._dependents)
        self.assertEqual({leaf}, root3._dependents)

    def test_initial_data(self):
        """Initial data of a source node can be set in the constructor"""
        node = SrcNode(data=5)
        self.assertEqual(5, node._data)

    def test_data_property_setter(self):
        """Data for a node can be set with the .data property"""
        root = SrcNode()
        leaf = OpNode(op=lambda data: data, inputs=OpNode.inputs(root))
        root.data = 5
        self.assertEqual(5, leaf.get_data())

    def test_data_property_getter(self):
        """Data of a node can be set with the .data property"""
        root = SrcNode(data=5)
        leaf = OpNode(op=lambda data: data, inputs=OpNode.inputs(root))
        self.assertEqual(5, leaf.data)


class BaseNodeGarbageCollectionTestCase(TestCase):
    """These tests show that nodes are garbage collected

    There is thus no need to use weakrefs when SrcNodes and OpNodes refer to
    each other as dependent nodes or inputs.

    """
    def test_garbage_collection(self):
        """Interconnected nodes are garbage collected"""
        source_node = SrcNode()
        operation_node = OpNode(op=lambda data: data,
                                inputs=OpNode.inputs(source_node))
        self.assertEqual(set([operation_node]), source_node._dependents)
        self.assertEqual((source_node,), operation_node._positional_inputs)
        source_ref = weakref.ref(source_node)
        operation_ref = weakref.ref(operation_node)
        del source_node
        del operation_node
        gc.collect()
        self.assertEqual(None, source_ref())
        self.assertEqual(None, operation_ref())

    def test_scope_garbage_collection(self):
        """Interconnected nodes which out of scope are garbage collected"""
        def inner():
            source_node = SrcNode()
            operation_node = OpNode(op=lambda data: data,
                                    inputs=OpNode.inputs(source_node))
            self.assertEqual(set([operation_node]), source_node._dependents)
            self.assertEqual((source_node,), operation_node._positional_inputs)
            return weakref.ref(source_node), weakref.ref(operation_node)

        input_ref, output_ref = inner()
        gc.collect()
        self.assertEqual(None, input_ref())
        self.assertEqual(None, output_ref())

    def test_garbage_collection_with_finalizer_data(self):
        """Interconnected nodes with gc-unfriendly data are gc'd"""
        class Val(object):
            def __del__(self):
                pass

        val = Val()
        source_node = SrcNode(data=val)
        operation_node = OpNode(op=lambda data: data,
                                inputs=OpNode.inputs(source_node))
        self.assertEqual(set([operation_node]), source_node._dependents)
        self.assertEqual((source_node,), operation_node._positional_inputs)
        self.assertEqual(val, source_node._data)
        source_ref = weakref.ref(source_node)
        operation_ref = weakref.ref(operation_node)
        del source_node
        del operation_node
        gc.collect()
        self.assertEqual(None, source_ref())
        self.assertEqual(None, operation_ref())


class NodeDependentTestCase(TestCase):
    """Test case for triggered dependent nodes"""

    def setUp(self):
        self.root = SrcNode('root')
        self.dependent = ConstantNode('dependent', triggered=False)
        self.root._connect(self.dependent)
        self.triggered = ConstantNode('triggered', triggered=True)
        self.root._connect(self.triggered)

    def test_keep_no_data(self):
        """Clearing NO_DATA doesn't trigger a node's dependents"""
        triggered_nodes = self.root.set_data(NO_DATA)
        self.assertEqual(set(), triggered_nodes)

    def test_set_data_triggers_dependents(self):
        """Setting data for a node with no data triggers dependents"""
        triggered_nodes = self.root.set_data(0)
        self.assertEqual({self.triggered}, triggered_nodes)

    def test_set_data_triggers_dependents(self):
        """Re-assigning SrcNode's current data doesn't trigger dependents"""
        self.root.set_data(0)
        triggered_nodes = self.root.set_data(0)
        self.assertEqual(set(), triggered_nodes)

    def test_get_triggered_dependents(self):
        """Setting data for a node with no data triggers dependents"""
        triggered_nodes = self.root._get_triggered_dependents()
        self.assertEqual({self.triggered}, triggered_nodes)

    def test_get_deep_triggered_dependents(self):
        """Setting data for a node with no data triggers dependents tree"""
        child1 = ConstantNode('child1', triggered=True)
        child2 = ConstantNode('child2', triggered=True)
        self.triggered._connect(child1)
        self.triggered._connect(child2)
        triggered_nodes = self.root._get_triggered_dependents()
        self.assertEqual({self.triggered, child1, child2}, triggered_nodes)


class Counting(object):
    """Mixin which counts calls to _get_triggered_dependents()"""

    def __init__(self, *args, **kwargs):
        super(Counting, self).__init__(*args, **kwargs)
        self.call_count = 0

    def _get_triggered_dependents(self, *args, **kwargs):
        self.call_count += 1
        return super(Counting, self)._get_triggered_dependents(*args,
                                                               **kwargs)


class CountingNode(Counting, ConstantNode):
    pass


class CountingSrcNode(Counting, SrcNode):
    pass


class TriggeredCacheTestCase(TestCase):
    """Test case for the cache of triggered nodes"""

    def setUp(self):
        self.root = CountingSrcNode('root')
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
                         _TRIGGERED_CACHE)

    def test_connect_clears_cache(self):
        """Connecting nodes invalidates the triggered nodes cache"""
        self.root._get_triggered_dependents()
        self.assertEqual({self.root: {self.branch, self.leaf1, self.leaf2}},
                         _TRIGGERED_CACHE)
        self.root._connect(CountingNode('leaf3'))
        self.assertEqual({}, _TRIGGERED_CACHE)

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


class NodeSetDataTestCase(TestCase):
    """Test case for SrcNode.set_data()"""

    def test_set_data(self):
        """Data set for a node with no data is stored in the object"""
        node = SrcNode('name')
        node.set_data(0)
        self.assertEqual(0, node._data)


class UpdateNodesTestCase(TestCase):
    """Test case for update_source_nodes*() methods"""

    def setUp(self):
        self.root = CountingSrcNode('root')
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
        """Updating a node only triggers its descendents"""
        triggered = update_source_nodes_get_triggered([(self.branch1, 2)])
        self.assertEqual({self.leaf1, self.leaf2}, triggered)

    def test_only_leafs_triggered_2(self):
        """Updating a node only triggers its descendents"""
        triggered = update_source_nodes_get_triggered([(self.branch2, 2)])
        self.assertEqual({self.leaf3, self.leaf4}, triggered)


class HomeAutomationTestCase(TestCase):
    """Test case illustrating a fictitious home automation use case"""

    def test_home_automation(self):
        """A simple example in the home automation domain"""
        brightness_1 = SrcNode()
        brightness_2 = SrcNode()
        brightness_sum = OpNode(
            op=lambda *args: sum(args),
            inputs=OpNode.inputs(brightness_1, brightness_2))

        def inverse(data):
            """Return the inverse of values in the range 0..510"""
            return 510 - data

        brightness_inverse = OpNode(op=inverse,
                                    inputs=OpNode.inputs(brightness_sum))

        lamp_power_changes = []

        def set_lamp_power(data):
            """Log changes to lamp power"""
            lamp_power_changes.append(data)

        _lamp_power = OpNode(op=set_lamp_power,
                             inputs=OpNode.inputs(brightness_inverse),
                             triggered=True)

        update_source_nodes_get_triggered([(brightness_1, 20),
                                           (brightness_2, 40)])

        self.assertEqual([450], lamp_power_changes)

        update_source_nodes_get_triggered([(brightness_1, 20),
                                           (brightness_2, 40)])

        self.assertEqual([450], lamp_power_changes)

        update_source_nodes_get_triggered([(brightness_1, 24),
                                           (brightness_2, 40)])

        self.assertEqual([450, 446], lamp_power_changes)


class MockOperationBase(object):
    def __call__(self, data):
        return data


class NoOutputTypeOperation(MockOperationBase):
    name = 'no'
    pass


class NoneOutputTypeOperation(MockOperationBase):
    name = 'none'
    output_type = None


class IntOutputTypeOperation(MockOperationBase):
    name = 'int_operation'
    output_type = int, np.integer


class NodeVerifyOutputTypeTestCase(TestCase):
    def setUp(self):
        self.source_node = SrcNode()

    def test_disabled_and_no_output_type(self):
        node = OpNode(op=NoOutputTypeOperation(),
                      inputs=OpNode.inputs(self.source_node))
        self.source_node.data = '42'
        node._evaluate()

    def test_disabled_and_none_output_type(self):
        node = OpNode(op=NoneOutputTypeOperation(),
                      inputs=OpNode.inputs(self.source_node))
        self.source_node.data = '42'
        node._evaluate()

    def test_disabled_and_correct_output_type(self):
        node = OpNode(op=IntOutputTypeOperation(),
                      inputs=OpNode.inputs(self.source_node))
        self.source_node.data = 42
        node._evaluate()

    def test_disabled_and_wrong_output_type(self):
        node = OpNode(op=IntOutputTypeOperation(),
                      inputs=OpNode.inputs(self.source_node))
        self.source_node.data = '42'
        node._evaluate()

    def test_enabled_and_no_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = OpNode(op=NoOutputTypeOperation(),
                          inputs=OpNode.inputs(self.source_node))
            self.source_node.data = '42'
            node._evaluate()

    def test_enabled_and_none_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = OpNode(op=NoneOutputTypeOperation(),
                          inputs=OpNode.inputs(self.source_node))
            self.source_node.data = '42'
            node._evaluate()

    def test_enabled_and_correct_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = OpNode(op=IntOutputTypeOperation(),
                          inputs=OpNode.inputs(self.source_node))
            self.source_node.data = 42
            node._evaluate()

    def test_enabled_and_wrong_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            with assert_raises(TypeError) as exc:
                node = OpNode(name='node',
                              op=IntOutputTypeOperation(),
                              inputs=OpNode.inputs(self.source_node))
                self.source_node.data = '42'
                node._evaluate()
            self.assertEqual(
                "The output data type 'str' for [node]\n"
                "doesn't match the expected type ['int', 'integer'] "
                'for operation "int_operation".', str(exc.exception))
