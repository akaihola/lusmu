"""Test suite for lusmu.vector

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""
import tempfile
from unittest import TestCase

from mock import patch
import joblib
from nose.tools import assert_raises, eq_
import numpy as np
import pandas as pd

from lusmu.core import NO_DATA
from lusmu.tests.test_core import (NoOutputTypeOperation,
                                   NoneOutputTypeOperation,
                                   IntOutputTypeOperation)
from lusmu.vector import SrcNode
from lusmu import vector
from lusmu.tests.tools import parameterize


def sum(*args):
    return sum(args)


class VectorEq(vector.VectorEquality):
    """Mock node class implementing the vector equality test"""
    def __init__(self, data):
        self._data = data


def test_scalar_equality():
    """Test cases for lusmu.vector.VectorEq._data_eq() with Python scalars"""

    @parameterize
    def check(data, other_data, expected):
        """Scalar node data {0} == {1}: {2}"""
        # pylint: disable=W0212
        #         Access to a protected member of a client class

        vector = VectorEq(data)
        assert expected == vector._data_eq(other_data)

    yield check(NO_DATA, NO_DATA, True)
    yield check(NO_DATA, 0, False)
    yield check(0, 0, True)
    yield check(0, 1, False)
    yield check(0, 0.0, False)
    yield check(0, 1.0, False)
    yield check(0.0, 0.0, True)
    yield check(0.0, 1.0, False)
    yield check('a', 'a', True)
    yield check('a', 'b', False)


def test_numpy_vector_equality():
    """Test cases for lusmu.vector.VectorEq._data_eq() with numpy arrays"""

    @parameterize
    def check(data, other_data, expected):
        """Vector node data {0} == {1}: {2}"""
        # pylint: disable=W0212
        #         Access to a protected member of a client class

        vector = VectorEq(np.array(data))
        assert expected == vector._data_eq(np.array(other_data))

    yield check([], [], True)
    yield check([1], [], False)
    yield check([], [2], False)
    yield check([3], [3], True)
    yield check([4], [4, 5], False)
    yield check([4], [4, 4], False)
    yield check([4, 5], [4], False)
    yield check([6, 7, 8], [6, 7, 8], True)
    yield check([9, np.nan], [9, np.nan], True)
    yield check([9, 10], [9, np.nan], False)


def test_numpy_vector_equality_others():
    """Test cases for lusmu.vector.VectorEq._data_eq() with complex data types
    """

    @parameterize
    def check(data, other_data, expected):
        """Vector node data {0} == {1}: {2}"""
        # pylint: disable=W0212
        #         Access to a protected member of a client class

        vector = VectorEq(data)
        assert expected == vector._data_eq(other_data)

    yield check(NO_DATA, np.array([[1,2],[3,4]]), False)
    yield check(np.array([[1,2],[3,4]]), np.array([[1,2],[3,4]]), True)
    yield check(np.array([[1,2],[3,4]]), np.array([[1,2],[3,5]]), False)
    yield check(np.array([[1,2],[3,4]]), [[1,2],[3,4]], False)
    yield check(np.array([[1,2]]), np.array([[1,2],[1,2]]), False)


def test_pandas_vector_equality():
    """Test cases for lusmu.vector.VectorEq._data_eq() with pandas Series"""

    @parameterize
    def check(data, index, other_data, other_index, expected):
        """Series node data {0}/{1} == {2}/{3}: {4}"""
        # pylint: disable=W0212
        #         Access to a protected member of a client class
        this = pd.Series(data, index=pd.to_datetime(index))
        other = pd.Series(other_data, index=pd.to_datetime(other_index))
        vector = VectorEq(this)

        assert expected == vector._data_eq(other)

    yield check([], [], [], [], True)
    yield check([1], ['2013-10-15'], [], [], False)
    yield check([], [], [2], ['2013-10-15'], False)
    yield check([3], ['2013-10-15'], [3], ['2013-10-15'], True)
    yield check([4], ['2013-10-15'], [4, 5],
                ['2013-10-15', '2013-10-16'],
                False)
    yield check([4, 5], ['2013-10-15', '2013-10-16'],
                [4], ['2013-10-15'],
                False)
    yield check([6, 7, 8], ['2013-10-15', '2013-10-16', '2013-10-17'],
                [6, 7, 8], ['2013-10-15', '2013-10-16', '2013-10-17'],
                True)
    yield check([6, 7, 8], ['2013-10-15', '2013-10-16', '2013-10-17'],
                [6, 7, 8], ['2013-10-15', '2013-10-16', '2013-10-18'],
                False)
    yield check([9, np.nan], ['2013-10-15', '2013-10-16'],
                [9, np.nan], ['2013-10-15', '2013-10-16'],
                True)
    yield check([9, np.nan], ['2013-10-15', '2013-10-16'],
                [9, np.nan], ['2013-10-15', '2013-10-17'],
                False)
    yield check([9, 10], ['2013-10-15', '2013-10-16'],
                [9, np.nan], ['2013-10-15', '2013-10-16'],
                False)


def test_mixed_vector_equality():
    """Test cases for lusmu.vector.VectorEq._data_eq() with pandas Series"""

    @parameterize
    def check(data, index, other_data, expected):
        """Series node data {0}/{1} == {2}: {3}"""
        # pylint: disable=W0212
        #         Access to a protected member of a client class
        this = pd.Series(data, index=pd.to_datetime(index))
        other = np.array(other_data)
        vector = VectorEq(this)

        assert expected == vector._data_eq(other)

    yield check([], [], [], False)
    yield check([1], ['2013-10-15'], [], False)
    yield check([], [], [2], False)
    yield check([3], ['2013-10-15'], [3], False)
    yield check([4], ['2013-10-15'], [4, 5], False)
    yield check([4, 5], ['2013-10-15', '2013-10-16'], [4], False)


class SrcNodeSetDataTestCase(TestCase):
    def test_no_data(self):
        source_node = vector.SrcNode()

        eq_(None, source_node.last_timestamp)

    def test_no_data(self):
        source_node = vector.SrcNode(data=NO_DATA)

        eq_(None, source_node.last_timestamp)

    def test_initial_data(self):
        source_node = vector.SrcNode(data=pd.Series([1, 2], [1001, 1002]))

        eq_(1002, source_node.last_timestamp)

    def test_set_data(self):
        source_node = vector.SrcNode()
        source_node.data = pd.Series([1, 2], index=[1001, 1002])

        eq_(1002, source_node.last_timestamp)

    def test_scalar_data(self):
        source_node = vector.SrcNode(data=100000.0)

        eq_(None, source_node.last_timestamp)

    def test_array_data(self):
        source_node = vector.SrcNode(data=np.array([1, 2]))

        eq_(None, source_node.last_timestamp)


def _pickle_unpickle(data):
    with tempfile.NamedTemporaryFile(delete=True) as pickle_file:
        pickle_file.close()

        joblib.dump(data, pickle_file.name)
        return joblib.load(pickle_file.name)


def test_pickling():
    @parameterize
    def check(node_class, attribute, value, expected):
        """{0.__name__}.{1} pickling works as expected"""
        node = node_class()
        setattr(node, attribute, value)

        unpickled_node = _pickle_unpickle(node)

        if isinstance(expected, type) and issubclass(expected, Exception):
            assert_raises(expected, getattr, unpickled_node, attribute)
        else:
            value = getattr(unpickled_node, attribute)
            if callable(expected):
                assert expected(value)
            elif isinstance(expected, np.ndarray):
                assert vector.vector_eq(expected, value)
            else:
                assert expected == value

    # arguments: (node class, attribute, data to set,
    #             expected data/exception/test)
    yield check(vector.SrcNode, 'name', 'constant',
                'constant')
    yield check(vector.SrcNode, '_data', 42.0,
                42.0)
    yield check(vector.SrcNode, '_data', NO_DATA,
                NO_DATA)
    yield check(vector.SrcNode, '_data', np.array([42.0]),
                np.array([42.0]))
    yield check(vector.SrcNode, 'last_timestamp', 1234,
                1234)
    yield check(vector.SrcNode, 'extra_attribute', 42.0,
                AttributeError)

    yield check(vector.OpNode, 'name', 'constant',
                'constant')
    yield check(vector.OpNode, '_data', 42.0,
                42.0)
    yield check(vector.OpNode, '_data', np.array([42.0]),
                np.array([42.0]))
    yield check(vector.OpNode, '_operation', sum,
                lambda _operation: _operation == sum)
    yield check(vector.OpNode, 'triggered', True,
                True)
    yield check(vector.OpNode, '_positional_inputs',
                (vector.SrcNode(name='foo'),),
                (lambda _positional_inputs:
                 [n.name for n in _positional_inputs] == ['foo']))
    yield check(vector.OpNode, '_keyword_inputs',
                {'foo': vector.SrcNode(name='bar')},
                (lambda _keyword_inputs:
                 {k: v.name for k, v in _keyword_inputs.items()}
                 == {'foo': 'bar'}))
    yield check(vector.OpNode, 'extra_attribute', 42.0,
                AttributeError)


def test_input_equality():
    @parameterize
    def check(_, a, b, expected):
        """SrcNode.__eq__ is {3} for {0}"""
        result = a == b
        eq_(expected, result)

    yield check('unnamed (auto-named) data inputs with no data',
                SrcNode(name=None, data=NO_DATA), SrcNode(name=None, data=NO_DATA),
                False)
    yield check('non-matching names',
                SrcNode(name='a', data=NO_DATA), SrcNode(name='b', data=NO_DATA),
                False)
    yield check('named vs. unnamed node',
                SrcNode(name='a', data=NO_DATA), SrcNode(name=None, data=NO_DATA),
                False)


class VectorNodeVerifyOutputTypeTestCase(TestCase):
    def setUp(self):
        self.source_node = SrcNode()

    def test_disabled_and_no_output_type(self):
        node = vector.OpNode(op=NoOutputTypeOperation(),
                             inputs=vector.OpNode.inputs(self.source_node))
        self.source_node.data = np.array(['42'])
        node._evaluate()

    def test_disabled_and_none_output_type(self):
        node = vector.OpNode(op=NoneOutputTypeOperation(),
                             inputs=vector.OpNode.inputs(self.source_node))
        self.source_node.data = np.array(['42'])
        node._evaluate()

    def test_disabled_and_correct_output_type(self):
        node = vector.OpNode(op=IntOutputTypeOperation(),
                             inputs=vector.OpNode.inputs(self.source_node))
        self.source_node.data = np.array([42])
        node._evaluate()

    def test_disabled_and_wrong_output_type(self):
        node = vector.OpNode(op=IntOutputTypeOperation(),
                             inputs=vector.OpNode.inputs(self.source_node))
        self.source_node.data = np.array(['42'])
        node._evaluate()

    def test_enabled_and_no_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = vector.OpNode(op=NoOutputTypeOperation(),
                                 inputs=vector.OpNode.inputs(self.source_node))
            self.source_node.data = np.array(['42'])
            node._evaluate()

    def test_enabled_and_none_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = vector.OpNode(op=NoneOutputTypeOperation(),
                                 inputs=vector.OpNode.inputs(self.source_node))
            self.source_node.data = np.array(['42'])
            node._evaluate()

    def test_enabled_and_correct_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            node = vector.OpNode(op=IntOutputTypeOperation(),
                                 inputs=vector.OpNode.inputs(self.source_node))
            self.source_node.data = np.array([42])
            node._evaluate()

    def test_enabled_and_wrong_output_type(self):
        with patch('lusmu.core.VERIFY_OUTPUT_TYPES', True):
            with assert_raises(TypeError) as exc:
                node = vector.OpNode(name='node',
                                     op=IntOutputTypeOperation(),
                                     inputs=vector.OpNode.inputs(self.source_node))
                self.source_node.data = np.array(['42'])
                node._evaluate()
            # The name of the NumPy string type is 'string_' in Python 2 but
            # 'str_' in Python 3.
            str_type_name = self.source_node.data.dtype.type.__name__
            expected = ("The output data type '{str}' for [node]\n"
                        "doesn't match the expected type ['int', 'integer'] "
                        'for operation "int_operation".'
                        .format(str=str_type_name))
            self.assertEqual(expected, str(exc.exception))
