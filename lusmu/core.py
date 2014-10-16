"""Core functionality of the lusmu library

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

# pylint: disable=W0212
#         Allow access to protected members of client classes
# pylint: disable=W0142
#         Allow * and ** magic

from collections import defaultdict
from functools import total_ordering
import itertools
import logging
import sys


LOG = logging.getLogger('lusmu.base')

# When developing, change this to True in order to verify the type consistency
# of Lusmu graphs.
VERIFY_OUTPUT_TYPES = False


if sys.version_info[0] == 2:
    def items(dictionary):
        """Return a set-like object, a view on key/value pairs of a dict"""
        return dictionary.viewitems()

    def values(dictionary):
        """Return an object providing a view on the values of a dictionary"""
        return dictionary.viewvalues()

    def get_func_name(function, default=None):
        """Return the name of the function, falling back to a default"""
        return getattr(function, 'func_name', default)
else:
    def items(dictionary):
        """Return a set-like object, a view on key/value pairs of a dict"""
        return dictionary.items()

    def values(dictionary):
        """Return an object providing a view on the values of a dictionary"""
        return dictionary.values()

    def get_func_name(function, default=None):
        """Return the name of the function, falling back to a default"""
        return getattr(function, '__name__', default)


_TRIGGERED_CACHE = {}


class _DIRTY(object):
    """Class definition for the dirty node special value"""

    def __str__(self):
        return 'DIRTY'

    def __repr__(self):
        return '<lusmu.base.DIRTY>'

    def __eq__(self, other):
        return self.__class__ == other.__class__


DIRTY = _DIRTY()


class BaseNode(object):
    """Base class for source and operation nodes"""

    _name_counters = defaultdict(int)

    def __init__(self, name=None, value=DIRTY):
        self.name = name or self._generate_name()
        self._value = value
        self._dependents = set()

    def _connect(self, dependent):
        """Set the given node as a dependent of this OpNode or SrcNode

        Immediately paints the new dependent node dirty if this node has
        already been evaluated or if a value has already been set for this
        source node.

        Connecting nodes always invalidates the triggered nodes cache.

        """
        if dependent not in self._dependents:
            self._dependents.add(dependent)
            if self._value is not DIRTY:
                dependent._set_value(DIRTY, get_triggered=False)
            _TRIGGERED_CACHE.clear()

    def _disconnect(self, dependent):
        """Remove given node from the set of dependents of this OpNode or SrcNode

        Immediately paints the new dependent node dirty if this node has
        previously been evaluated or if a value has previously been set for
        this source node.

        Disconnecting nodes always invalidates the triggered nodes cache.

        """
        if dependent in self._dependents:
            self._dependents.remove(dependent)
            if self._value is not DIRTY:
                dependent._set_value(DIRTY, get_triggered=False)
            _TRIGGERED_CACHE.clear()

    def _set_value(self, value, get_triggered=True):
        """Set a new value for this OpNode or SrcNode

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        When called by ``set_value`` from external code, the ``get_triggered``
        argument must be ``True`` so the return value is cached.  Internal
        calls set ``get_triggered=False`` so memory isn't wasted for caching
        the triggered dependents of intermediate nodes.

        This private method can be used as a debugging tool to set values of
        operation nodes.

        """
        # test if neither, one of or both the old and the new value are DIRTY
        dirty_count = len([v for v in (value, self._value) if v is DIRTY])
        if dirty_count == 2:
            # both DIRTY, no need to touch anything
            return set()
        if dirty_count == 0 and self._value_eq(value):
            # both non-DIRTY but equal, no need to touch anything
            return set()
        # either one is DIRTY, or values aren't equal, update the value and
        # paint the dependent nodes dirty
        self._value = value
        self._set_dependents_dirty()
        if get_triggered:
            return self._get_triggered_dependents()

    def _value_eq(self, other_value):
        return self._value == other_value

    def get_value(self):
        """Return the value of the object"""
        raise NotImplementedError('The get_value() method must be defined '
                                  'for subclasses of BaseNode')

    def _get_triggered_dependents(self, make_cache=True):
        """Return the set of triggered dependent nodes

        The set includes nodes which are marked as triggered and are included
        in the dependent chain from this OpNode or SrcNode.

        The result is cached for the OpNode or SrcNode if ``make_cache == True``,
        but caching is suppressed for recursively walked dependent nodes.  This
        way we only use cache memory only for operation and source nodes whose
        triggered dependents are queried from external code.

        """
        if self in _TRIGGERED_CACHE:
            return _TRIGGERED_CACHE[self]
        triggered = set()
        for dependent in self._dependents:
            if dependent.triggered:
                triggered.add(dependent)
            triggered |= dependent._get_triggered_dependents(make_cache=False)
        if make_cache:
            _TRIGGERED_CACHE[self] = triggered
        return triggered

    def _set_dependents_dirty(self):
        """Paint all dependent nodes dirty

        Paints direct dependent nodes dirty, which causes recursive painting
        for the whole dependent nodes tree.

        """
        for dependent in self._dependents:
            dependent._set_value(DIRTY, get_triggered=False)

    def _generate_name(self):
        """Generate a unique name for this OpNode or SrcNode object

        The name includes:

        * the name of the class
        * an auto-incremented number

        """
        counters = self._name_counters
        template = '{class_name}-{counter}'
        counters[self.__class__] += 1
        return template.format(class_name=self.__class__.__name__,
                               counter=counters[self.__class__])

    def __unicode__(self):
        return unicode(self.get_value())

    def __repr__(self):
        return ('<{self.__class__.__name__} {self.name}: {self._value}>'
                .format(self=self))


class SrcNode(BaseNode):
    """The source node class for reactive programming

    Constructor arguments
    ---------------------

    name (optional): string
            The internal name of the source node. Used in the
            ``__repr__`` of the object. If omitted, a name is
            automatically generated.

    value (optional):
            The initial value for the source node.

    Examples of source nodes::

        >>> source_1 = SrcNode()  # no name, no default value
        >>> source_2 = SrcNode(value=10.0)  # with a default value
        >>> exponent = SrcNode(name='exponent')  # named source node
        >>> sensor = SrcNode(name='sensor', value=-5.3)  # named, with default

    """
    def get_value(self):
        """Return the value of the source node"""
        return self._value

    def set_value(self, new_value):
        """Set a new value for an source node

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        """
        return self._set_value(new_value, get_triggered=True)

    value = property(get_value, set_value)


@total_ordering
class OpNode(BaseNode):
    """The operation node class for reactive programming

    Constructor arguments
    ---------------------

    name (optional): string
            The internal name of the node. Used in the ``__repr__`` of the
            object. If omitted, a name is automatically generated.

    op: callable(*positional_inputs, **keyword_inputs)
            The function for calculating the value of an operation node.
            Values from inputs are provided in positional and keyword arguments
            as defined in the ``inputs=`` argument.

    inputs (optional): ((SrcNode/OpNode, ...), {key: SrcNode/OpNode, ...})
            The nodes whose values are used as inputs for
            the operation. This argument can be created with
            ``OpNode.inputs()`` which provides a cleaner syntax.

    triggered: boolean (default=False)
            ``True`` is this OpNode shoud be automatically evaluated when any
            OpNode or SrcNode it depends on change value

    Examples of operation nodes::

        >>> source_1, source_2, exponent = [SrcNode() for i in range(3)]
        >>> # sum OpNode with two positional inputs
        >>> sum_node = OpNode(op=lambda *args: sum(args),
        ...                   inputs=OpNode.inputs(source_1, source_2))
        >>> # triggered (auto-calculated) OpNode with two keyword inputs
        >>> triggered_node = OpNode(
        ...     op=lambda a, x: a ** x,
        ...     inputs=OpNode.inputs(a=source_1, x=exponent),
        ...     triggered=True)

    """
    def __init__(self,
                 name=None,
                 op=None,
                 inputs=((), None),
                 triggered=False):
        self._operation = op  # must be set before generating name
        super(OpNode, self).__init__(name, value=DIRTY)
        self.triggered = triggered
        self._positional_inputs = ()
        self._keyword_inputs = {}
        self.set_inputs(*inputs[0], **inputs[1] or {})
        self._set_dependents_dirty()

    def _evaluate(self):
        """Calculate the value for the OpNode

        Calls the operation of the node using values from the inputs of the
        node. Returns the result of the operation function.

        This function can also be overridden in subclasses if a class-based
        approach to defining operations is preferred.

        """
        if not self._operation:
            raise NotImplementedError('You must define the op= argument '
                                      'when instantiating the operation node')
        positional_values = [i.get_value()
                             for i in self._positional_inputs]
        keyword_values = {name: i.get_value()
                          for name, i in items(self._keyword_inputs)}
        value = self._operation(*positional_values, **keyword_values)
        if ((VERIFY_OUTPUT_TYPES
             and getattr(self._operation, 'output_type', None) is not None)):
            # Output type checking has been enabled, and the node's operation
            # does specify the expected output type. Check that the calculated
            # value matches that type.
            self._verify_output_type(value)
        return value

    @staticmethod
    def inputs(*args, **kwargs):
        """Construct a value for the inputs= kwarg of the constructor

        Allows writing this::

            >>> inputs = [SrcNode() for i in range(4)]
            >>> node = OpNode(inputs=OpNode.inputs(
            ...     inputs[0], inputs[1],
            ...     kw1=inputs[2], kw2=inputs[3]))

        instead of this::

            >>> node = OpNode(inputs=([inputs[0], inputs[1]],
            ...                       {'kw1': inputs[2], 'kw2': inputs[3]}))

        """
        return args, kwargs

    def _verify_output_type(self, value):
        """Assert that the given value matches the operation's output type

        This check should be run only in development if the developer wants to
        ensure the consistency of a graph's types.

        This method may only be called if the node's operation has a non-None
        ``output_type`` attribute.

        Arguments
        ---------
        value: The value whose type is to be checked

        Raises
        ------
        TypeError: The value doesn't match the desired output type of the
                   node's operation

        """
        if not isinstance(value, self._operation.output_type):
            output_type = self._operation.output_type
            output_type_name = ([v.__name__ for v in output_type]
                                if isinstance(output_type, tuple)
                                else output_type.__name__)
            raise TypeError(
                "The output value type {value.__class__.__name__!r} "
                "for [{self.name}]\n"
                "doesn't match the expected type {output_type} for operation "
                '"{self._operation.name}".'
                .format(value=value, output_type=output_type_name, self=self))

    def set_inputs(self, *args, **kwargs):
        """Replace current positional and keyword inputs"""
        for inp in self._iterate_inputs():
            inp._disconnect(self)
        self._positional_inputs = args
        self._keyword_inputs = kwargs
        for inp in self._iterate_inputs():
            inp._connect(self)

    def get_value(self):
        """Return OpNode value, evaluate if needed and mark dependents dirty"""
        if self._value is DIRTY:
            self._value = self._evaluate()
            LOG.debug('EVALUATED %s: %s', self.name, self._value)
            self._set_dependents_dirty()
        return self._value

    def set_value(self, new_value):
        """Set a new value for an operation node

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        """
        return self._set_value(new_value, get_triggered=True)

    value = property(get_value, set_value)

    def _iterate_inputs(self):
        """Iterate through positional and keyword inputs"""
        return itertools.chain(self._positional_inputs,
                               values(self._keyword_inputs))

    def _generate_name(self):
        """Generate a unique name for this OpNode object

        The name includes:

        * the name of the node class
        * the function name of the ``_operation`` if it's defined
          and isn't a lambda
        * an auto-incremented number

        """
        operation_name = get_func_name(self._operation, '<lambda>')
        if operation_name == '<lambda>':
            return super(OpNode, self)._generate_name()
        counters = self._name_counters
        counters[self.__class__, operation_name] += 1
        template = '{class_name}-{operation_name}-{counter}'
        return template.format(
            class_name=self.__class__.__name__,
            operation_name=operation_name,
            counter=counters[self.__class__, operation_name])

    def __lt__(self, other):
        return self.name < other.name


def update_source_nodes_iter(nodes_and_values):
    """Update values of multiple source nodes and trigger dependent nodes

    This is a generator which iterates through the set of triggered dependent
    nodes.

    """
    triggered = set()
    for node, new_value in nodes_and_values:
        triggered |= node._set_value(new_value)
    for node in triggered:
        node.get_value()  # trigger evaluation
        yield node


def update_source_nodes(nodes_and_values):
    """Update values of multiple source nodes and trigger dependent nodes

    Use this variant of the ``update_source_nodes*`` functions if you don't
    need to access the set of triggered dependent nodes.

    """
    for _node in update_source_nodes_iter(nodes_and_values):
        pass


def update_source_nodes_get_triggered(nodes_and_values):
    """Update values of multiple source nodes and trigger dependent nodes

    This variant of the ``update_source_nodes*`` functions returns triggered
    dependent nodes as a Python set.

    """
    return set(update_source_nodes_iter(nodes_and_values))
