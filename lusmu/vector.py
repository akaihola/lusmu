# -*- encoding: utf-8 -*-

"""The lazy evaluation graph adapted for numpy arrays and pandas Series

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

# pylint: disable=W0611
#         update_inputs is provided as a convenience for importing it from the
#         same place as the Input and OpNode classes
# pylint: disable=R0903
#         mixins have few public methods, that's ok

import logging
from lusmu.core import (DIRTY,
                        Input as LusmuInput,
                        OpNode as LusmuOpNode,
                        update_inputs)
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
    """Mixin for extending Lusmu Inputs and Nodes to work with vector values"""
    def _value_eq(self, other_value):
        """Replace the equality test of Input/OpNode values

        Lusmu uses the ``==`` operator by default.  It doesn't work correctly
        with vectors which have more than one value – ``bool(vec1 == vec2)``
        raises an exception.

        """
        # pylint: disable=E1101
        #         (Instance of VectorEquality has no _value member)
        #         This class will be mixed into ones that have _value
        a = self._value
        b = other_value
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
                a_ind._value = a.index.values.astype(float)
                return a_ind._value_eq(b.index.values.astype(float))
            return True
        except (AttributeError, TypeError):
            # not pandas or numpy objects
            return (
                type(self._value) == type(other_value) and
                self._value == other_value)


class NodePickleMixin(object):
    """Mixin defining the attributes to pickle for all node types"""
    _state_attributes = 'name', '_dependents', '_value'

    def __getstate__(self):
        return {key: getattr(self, key)
                for key in self._state_attributes}


class Input(NodePickleMixin, VectorEquality, LusmuInput):
    """Vector compatible Lusmu Input

    The value of the input node is always set dirty when unpickling.

    """
    _state_attributes = NodePickleMixin._state_attributes + ('last_timestamp',)

    def __init__(self, name=None, value=DIRTY):
        super(Input, self).__init__(name=name, value=value)
        self.last_timestamp = self._get_max_timestamp(value)

    @staticmethod
    def _get_max_timestamp(value):
        """Return the latest timestamp in the Series

        Arguments
        ---------
        value: pandas.Series with a timestamp index

        """
        if isinstance(value, pd.Series) and len(value):
            return value.index[-1]

    def _set_value(self, value, get_triggered=True):
        """Keep track of latest timestamp processed"""
        new_last_timestamp = self._get_max_timestamp(value)
        if new_last_timestamp:
            self.last_timestamp = new_last_timestamp
        return super(Input, self)._set_value(value, get_triggered=get_triggered)

    def __eq__(self, other):
        """Equality comparison provided for unit test convenience"""
        return self.name == other.name and self._value_eq(other.value)

    # In Python 3, the __hash__ method needs to be defined when __eq__ is
    # defined:
    __hash__ = LusmuInput.__hash__


class OpNode(NodePickleMixin, VectorEquality, LusmuOpNode):
    """Vector compatible Lusmu Node"""
    _state_attributes = (NodePickleMixin._state_attributes +
                         ('_action',
                          'triggered',
                          '_positional_inputs',
                          '_keyword_inputs'))

    def _verify_output_type(self, value):
        """Assert that the given value matches the action's output type

        This adds NumPy/Pandas dtype support to output type verification.

        """
        if hasattr(value, 'dtype'):
            if not issubclass(value.dtype.type, self._action.output_type):
                output_type = self._action.output_type
                output_type_name = ([v.__name__ for v in output_type]
                                    if isinstance(output_type, tuple)
                                    else output_type.__name__)

                raise TypeError(
                    "The output value type {value.dtype.type.__name__!r} "
                    "for [{self.name}]\n"
                    "doesn't match the expected type "
                    "{output_type_name} for action "
                    '"{self._action.name}".'
                    .format(output_type_name=output_type_name,
                            value=value,
                            self=self))
        else:
            super(OpNode, self)._verify_output_type(value)

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
