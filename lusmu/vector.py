# -*- encoding: utf-8 -*-

"""The lazy evaluation graph adapted for numpy arrays and pandas Series

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

# pylint: disable=W0611
#         update_source_nodes is provided as a convenience for importing it from the
#         same place as the SrcNode and OpNode classes
# pylint: disable=R0903
#         mixins have few public methods, that's ok

import logging
from lusmu.core import (NO_DATA,
                        SrcNode as LusmuSrcNode,
                        OpNode as LusmuOpNode,
                        update_source_nodes)
import numexpr as ne
import numpy as np
import pandas as pd


def vector_eq(a, b):
    """Return True if vectors are equal, comparing NaNs correctly too

    Arguments
    ---------
    a, b: numpy.array
                The vectors to compare

    """
    # pylint: disable=C0103
    #         allow one-letter function arguments

    a_length, b_length = len(a), len(b)
    if a_length != b_length:
        # comparing np.array([]) to np.array([1]) only works this way
        return False
    if not a_length and not b_length:
        # dtypes might be wrong for empty arrays
        return True
    # Consider NaNs equal; see http://stackoverflow.com/a/10821267
    return np.all(ne.evaluate('(a==b)|((a!=a)&(b!=b))'))


class VectorEquality(object):
    """Mixin to extend Lusmu SrcNodes and OpNodes to work with vector data"""
    def _data_eq(self, other_data):
        """Replace the equality test of SrcNode/OpNode data

        Lusmu uses the ``==`` operator by default.  It doesn't work correctly
        with vectors which have more than one value – ``bool(vec1 == vec2)``
        raises an exception.

        """
        # pylint: disable=E1101
        #         (Instance of VectorEquality has no _data member)
        #         This class will be mixed into ones that have _data
        a = self._data
        b = other_data
        try:
            if type(a) != type(b):
                return False
            if len(a)==0 and len(b)==0:
                return True
            if a.shape != b.shape:
                return False
            if not np.all(ne.evaluate('(a==b)|((a!=a)&(b!=b))')):
                return False
            if hasattr(a, 'index') and hasattr(b, 'index'):
                # The values are Pandas Series with time indices. Compare time
                # indices, too.
                a_ind = VectorEquality()
                # FIXME: We should support non-number indices as well!
                a_ind._data = a.index.values.astype(float)
                return a_ind._data_eq(b.index.values.astype(float))
            return True
        except (AttributeError, TypeError):
            # not pandas or numpy objects
            return (
                type(self._data) == type(other_data) and
                self._data == other_data)


class NodePickleMixin(object):
    """Mixin defining the attributes to pickle for all node types"""
    _state_attributes = 'name', '_dependents', '_data'

    def __getstate__(self):
        return {key: getattr(self, key)
                for key in self._state_attributes}


class SrcNode(NodePickleMixin, VectorEquality, LusmuSrcNode):
    """Vector compatible Lusmu source node

    The data of the source node is always cleared when unpickling.

    """
    _state_attributes = NodePickleMixin._state_attributes + ('last_timestamp',)

    def __init__(self, name=None, data=NO_DATA):
        super(SrcNode, self).__init__(name=name, data=data)
        self.last_timestamp = self._get_max_timestamp(data)

    @staticmethod
    def _get_max_timestamp(data):
        """Return the latest timestamp in the Series

        Arguments
        ---------
        data: pandas.Series with a timestamp index

        """
        if isinstance(data, pd.Series) and len(data):
            return data.index[-1]

    def _set_data(self, data, get_triggered=True):
        """Keep track of latest timestamp processed"""
        new_last_timestamp = self._get_max_timestamp(data)
        if new_last_timestamp:
            self.last_timestamp = new_last_timestamp
        return super(SrcNode, self)._set_data(data,
                                              get_triggered=get_triggered)

    def __eq__(self, other):
        """Equality comparison provided for unit test convenience"""
        return self.name == other.name and self._data_eq(other.data)

    # In Python 3, the __hash__ method needs to be defined when __eq__ is
    # defined:
    __hash__ = LusmuSrcNode.__hash__


class OpNode(NodePickleMixin, VectorEquality, LusmuOpNode):
    """Vector compatible Lusmu operation node"""
    _state_attributes = (NodePickleMixin._state_attributes +
                         ('_operation',
                          'triggered',
                          '_ordered_input_ports',
                          '_named_input_ports'))

    def _verify_output_type(self, data):
        """Assert that the given data matches the operation's output type

        This adds NumPy/Pandas dtype support to output type verification.

        """
        if hasattr(data, 'dtype'):
            if not issubclass(data.dtype.type, self._operation.output_type):
                output_type = self._operation.output_type
                output_type_name = ([v.__name__ for v in output_type]
                                    if isinstance(output_type, tuple)
                                    else output_type.__name__)

                raise TypeError(
                    "The output data type {data.dtype.type.__name__!r} "
                    "for [{self.name}]\n"
                    "doesn't match the expected type "
                    "{output_type_name} for operation "
                    '"{self._operation.name}".'
                    .format(output_type_name=output_type_name,
                            data=data,
                            self=self))
        else:
            super(OpNode, self)._verify_output_type(data)

    def _evaluate(self):
        """Log a message when evaluating a node"""
        # pylint: disable=E1101
        #         self.name comes from lusmu
        logger = logging.getLogger(__name__)
        logger.debug('[%s]._evaluate()', self.name)
        return super(OpNode, self)._evaluate()

    def __eq__(self, other):
        """Equality comparison provided for unit test convenience"""
        return self.__dict__ == other.__dict__

    # In Python 3, the __hash__ method needs to be defined when __eq__ is
    # defined:
    __hash__ = LusmuOpNode.__hash__
