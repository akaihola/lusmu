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


class _NoData(object):
    """Class definition for the 'missing data' special value"""

    def __str__(self):
        return 'NO_DATA'

    def __repr__(self):
        return '<lusmu.base.NO_DATA>'

    def __eq__(self, other):
        return self.__class__ == other.__class__


NO_DATA = _NoData()


class BaseNode(object):
    """Base class for source and operation nodes"""

    _name_counters = defaultdict(int)

    def __init__(self, name=None, data=NO_DATA):
        self.name = name or self._generate_name()
        self._data = data
        self._dependents = set()

    def _connect(self, dependent):
        """Set the given node as a dependent of this OpNode or SrcNode

        Immediately clears data from the new dependent node if this node has
        already been evaluated or if data has already been set for this
        source node.

        Connecting nodes always invalidates the triggered nodes cache.

        """
        if dependent not in self._dependents:
            self._dependents.add(dependent)
            if self._data is not NO_DATA:
                dependent._set_data(NO_DATA, get_triggered=False)
            _TRIGGERED_CACHE.clear()

    def _disconnect(self, dependent):
        """Remove given node from the set of dependents of this OpNode or SrcNode

        Immediately clears data from the new dependent node if this node has
        previously been evaluated or if data has previously been set for
        this source node.

        Disconnecting nodes always invalidates the triggered nodes cache.

        """
        if dependent in self._dependents:
            self._dependents.remove(dependent)
            if self._data is not NO_DATA:
                dependent._set_data(NO_DATA, get_triggered=False)
            _TRIGGERED_CACHE.clear()

    def _set_data(self, data, get_triggered=True):
        """Set new data for this OpNode or SrcNode

        If this caused the value of the data to change, clears data from
        dependent nodes and returns the set of those dependent nodes which are
        marked "triggered" and should be re-evaluated.

        When called by ``set_data`` from external code, the ``get_triggered``
        argument must be ``True`` so the return value is cached.  Internal
        calls set ``get_triggered=False`` so memory isn't wasted for caching
        the triggered dependents of intermediate nodes.

        This private method can be used as a debugging tool to set data of
        operation nodes.

        """
        # test if values of neither, one of or both old and new data are
        # NO_DATA
        no_data_count = len([v for v in (data, self._data) if v is NO_DATA])
        if no_data_count == 2:
            # both NO_DATA, no need to touch anything
            return set()
        if no_data_count == 0 and self._data_eq(data):
            # both non-NO_DATA but equal, no need to touch anything
            return set()
        # either one is NO_DATA, or data values aren't equal, update the data
        # and clear data from dependent nodes
        self._data = data
        self._clear_dependents_data()
        if get_triggered:
            return self._get_triggered_dependents()

    def _data_eq(self, other_data):
        return self._data == other_data

    def get_data(self):
        """Return the data of the object"""
        raise NotImplementedError('The get_data() method must be defined '
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

    def _clear_dependents_data(self):
        """Clear data from all dependent nodes

        Clears data from direct dependent nodes , which causes recursive
        clearing of the whole dependent nodes tree.

        """
        for dependent in self._dependents:
            dependent._set_data(NO_DATA, get_triggered=False)

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
        return unicode(self.get_data())

    def __repr__(self):
        return ('<{self.__class__.__name__} {self.name}: {self._data}>'
                .format(self=self))


class SrcNode(BaseNode):
    """The source node class for reactive programming

    Constructor arguments
    ---------------------

    name (optional): string
            The internal name of the source node. Used in the
            ``__repr__`` of the object. If omitted, a name is
            automatically generated.

    data (optional):
            Initial data for the source node.

    Examples of source nodes::

        >>> source_1 = SrcNode()  # no name, no default data
        >>> source_2 = SrcNode(data=10.0)  # with default data
        >>> exponent = SrcNode(name='exponent')  # named source node
        >>> sensor = SrcNode(name='sensor', data=-5.3)  # named, with default

    """
    def get_data(self):
        """Return the value of the data for the source node"""
        return self._data

    def set_data(self, new_data):
        """Set new data for a source node

        If this caused the data value to change, clears data from dependent
        nodes and returns the set of those dependent nodes which are marked
        "triggered" and should be re-evaluated.

        """
        return self._set_data(new_data, get_triggered=True)

    data = property(get_data, set_data)


@total_ordering
class OpNode(BaseNode):
    """The operation node class for reactive programming

    Constructor arguments
    ---------------------

    name (optional): string
            The internal name of the node. Used in the ``__repr__`` of the
            object. If omitted, a name is automatically generated.

    op: callable(*positional_inputs, **keyword_inputs)
            The function for calculating the result data of an operation node.
            Data from inputs is provided in positional and keyword arguments
            as defined in the ``inputs=`` argument.

    inputs (optional): ((SrcNode/OpNode, ...), {key: SrcNode/OpNode, ...})
            The nodes whose data is used as inputs for
            the operation. This argument can be created with
            ``OpNode.inputs()`` which provides a cleaner syntax.

    triggered: boolean (default=False)
            ``True`` is this OpNode shoud be automatically evaluated when data
            of any OpNode or SrcNode it depends on changes

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
        super(OpNode, self).__init__(name, data=NO_DATA)
        self.triggered = triggered
        self._positional_inputs = ()
        self._keyword_inputs = {}
        self.set_inputs(*inputs[0], **inputs[1] or {})
        self._clear_dependents_data()

    def _evaluate(self):
        """Calculate the result data for the OpNode

        Calls the operation of the node using data from inputs of the
        node. Returns the result of the operation function.

        This function can also be overridden in subclasses if a class-based
        approach to defining operations is preferred.

        """
        if not self._operation:
            raise NotImplementedError('You must define the op= argument '
                                      'when instantiating the operation node')
        positional_data = [i.get_data()
                           for i in self._positional_inputs]
        keyword_data = {name: i.get_data()
                        for name, i in items(self._keyword_inputs)}
        data = self._operation(*positional_data, **keyword_data)
        if ((VERIFY_OUTPUT_TYPES
             and getattr(self._operation, 'output_type', None) is not None)):
            # Output type checking has been enabled, and the node's operation
            # does specify the expected output type. Check that the calculated
            # data matches that type.
            self._verify_output_type(data)
        return data

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

    def _verify_output_type(self, data):
        """Assert that the given data matches the operation's output type

        This check should be run only in development if the developer wants to
        ensure the consistency of a graph's types.

        This method may only be called if the node's operation has a non-None
        ``output_type`` attribute.

        Arguments
        ---------
        data: The data whose type is to be checked

        Raises
        ------
        TypeError: The data doesn't match the desired output type of the
                   node's operation

        """
        if not isinstance(data, self._operation.output_type):
            output_type = self._operation.output_type
            output_type_name = ([v.__name__ for v in output_type]
                                if isinstance(output_type, tuple)
                                else output_type.__name__)
            raise TypeError(
                "The output data type {data.__class__.__name__!r} "
                "for [{self.name}]\n"
                "doesn't match the expected type {output_type} for operation "
                '"{self._operation.name}".'
                .format(data=data, output_type=output_type_name, self=self))

    def set_inputs(self, *args, **kwargs):
        """Replace current positional and keyword inputs"""
        for inp in self._iterate_inputs():
            inp._disconnect(self)
        self._positional_inputs = args
        self._keyword_inputs = kwargs
        for inp in self._iterate_inputs():
            inp._connect(self)

    def get_data(self):
        """Return OpNode data, evaluate if needed, clear data in dependents"""
        if self._data is NO_DATA:
            self._data = self._evaluate()
            LOG.debug('EVALUATED %s: %s', self.name, self._data)
            self._clear_dependents_data()
        return self._data

    def set_data(self, new_data):
        """Set new data for an operation node

        If this caused the data value to change, clears data from dependent
        nodes and returns the set of those dependent nodes which are marked
        "triggered" and should be re-evaluated.

        """
        return self._set_data(new_data, get_triggered=True)

    data = property(get_data, set_data)

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


def update_source_nodes_iter(nodes_and_data):
    """Update data of multiple source nodes and trigger dependent nodes

    This is a generator which iterates through the set of triggered dependent
    nodes.

    """
    triggered = set()
    for node, new_data in nodes_and_data:
        triggered |= node._set_data(new_data)
    for node in triggered:
        node.get_data()  # trigger evaluation
        yield node


def update_source_nodes(nodes_and_data):
    """Update data of multiple source nodes and trigger dependent nodes

    Use this variant of the ``update_source_nodes*`` functions if you don't
    need to access the set of triggered dependent nodes.

    """
    for _node in update_source_nodes_iter(nodes_and_data):
        pass


def update_source_nodes_get_triggered(nodes_and_data):
    """Update data of multiple source nodes and trigger dependent nodes

    This variant of the ``update_source_nodes*`` functions returns triggered
    dependent nodes as a Python set.

    """
    return set(update_source_nodes_iter(nodes_and_data))
