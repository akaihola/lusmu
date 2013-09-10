"""Core functionality of the lusmu library"""

# pylint: disable=W0212
#         Allow access to protected members of client classes

from collections import defaultdict
import itertools
import logging


LOG = logging.getLogger('lusmu.base')


_TRIGGERED_CACHE = {}


class DIRTY:
    def __str__(self):
        return 'DIRTY'

    def __repr__(self):
        return '<lusmu.base.DIRTY>'
DIRTY = DIRTY()


class Node(object):
    """Generic Node class for reactive programming

    Common constructor arguments:
      name (optional): The internal name of the node. Used in the
                       ``__repr__`` of the object. If omitted, a name is
                       automatically generated.

    Optional arguments for *input nodes*:
      value (optional): The initial value for an input node. Must be
                        omitted for calculated nodes.

    Optional arguments for *calculated nodes*:
      action (optional): The function for calculating the value of a
                         calculated node. Must be omitted for input nodes.
      inputs (optional): The nodes whose values are used as inputs for the
                         action. Must be omitted for input nodes.
      triggered: Should this node be automatically evaluated when any of
                 its depended nodes changes value

    Examples of input nodes::

        >>> input_1 = Node()  # no name, no default value
        >>> input_2 = Node(value=10.0)  # node with a default value
        >>> exponent = Node(name='exponent')  # named node
        >>> sensor = Node(name='sensor', value=-5.3)  # named, with default

    Examples of calculated nodes::

        >>> # sum node with two positional inputs
        >>> sum_node = Node(action=lambda *args: sum(args),
        ...                 inputs=Node.inputs(input_1, input_2))
        >>> # triggered (auto-calculated) node with two keyword inputs
        >>> triggered_node = Node(
        ...     action=lambda a, x: a ** x,
        ...     inputs=Node.inputs(a=input_1, x=exponent),
        ...     triggered=True)

    """
    _name_counters = defaultdict(int)

    def __init__(self,
                 name=None,
                 action=None,
                 value=DIRTY,
                 inputs=((), None),
                 triggered=False):
        self._action = action  # must be set before generating name
        self.name = name or self._generate_name()
        self.triggered = triggered
        self._value = DIRTY  # must be set before .set_inputs()

        self._dependents = set()
        self._positional_inputs = ()
        self._keyword_inputs = {}
        self.set_inputs(*inputs[0], **inputs[1] or {})

        if value is not DIRTY:
            # set initial value after connections have been set up
            self.set_value(value)

    @staticmethod
    def inputs(*args, **kwargs):
        """Construct a value for the inputs= kwarg of the constructor

        Allows writing this::

            >>> Node(inputs=Node.inputs(input1, input2,
            ...                         kw1=input3, kw2=input4)

        instead of this::

            >>> Node(inputs=([input1, input2],
            ...              {'kw1': input3, 'kw2': input4})))

        """
        return args, kwargs

    def set_inputs(self, *args, **kwargs):
        """Replace current positional and keyword inputs"""
        for node in self._iterate_inputs():
            node._disconnect(self)
        self._positional_inputs = args
        self._keyword_inputs = kwargs
        for node in self._iterate_inputs():
            node._connect(self)

    def get_value(self):
        """Return node value, evaluate if needed and paint dependents dirty"""
        if self._value is DIRTY:
            self._value = self._evaluate()
            LOG.debug('EVALUATED %s: %s', self.name, self._value)
            self._set_dependents_dirty()
        return self._value

    def set_value(self, new_value):
        """Set a new value for an input node (actionless node)

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        """
        if self._action:
            raise ValueError("'Can't set the value of a Node "
                             'which has an action')
        return self._set_value(new_value, make_cache=True)

    value = property(get_value, set_value)

    def _generate_name(self):
        """Generate a unique name for this Node object

        The name includes:

        * the name of the node class
        * the function name of the ``_action`` if it's defined
          and isn't a lambda
        * an auto-incremented number

        """
        counters = self._name_counters
        action_name = getattr(self._action, 'func_name', '<lambda>')
        if action_name != '<lambda>':
            template = '{class_name}-{action_name}-{counter}'
        else:
            template = '{class_name}-{counter}'
        counters[self.__class__, action_name] += 1
        return template.format(class_name=self.__class__.__name__,
                               action_name=action_name,
                               counter=counters[self.__class__, action_name])

    def _iterate_inputs(self):
        """Iterate through positional and keyword inputs"""
        return itertools.chain(self._positional_inputs,
                               self._keyword_inputs.itervalues())

    def _connect(self, dependent):
        """Set the given node as a dependent of this node

        Immediately paints the new dependent dirty if this node has already
        been evaluated.

        Connecting nodes always invalidates the triggered nodes cache.

        """
        if dependent not in self._dependents:
            self._dependents.add(dependent)
            if self._value is not DIRTY:
                dependent._set_value(DIRTY, make_cache=False)
            _TRIGGERED_CACHE.clear()

    def _disconnect(self, dependent):
        """Remove the given node from the set of dependents of this node

        Immediately paints the removed dependent dirty if this node has
        previously been evaluated.

        Disconnecting nodes always invalidates the triggered nodes cache.

        """
        if dependent in self._dependents:
            self._dependents.remove(dependent)
            if self._value is not DIRTY:
                dependent._set_value(DIRTY, make_cache=False)
            _TRIGGERED_CACHE.clear()

    def _set_value(self, value, make_cache=True):
        """Set a new value for this node

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        When called by ``set_value`` from external code, the ``make_cache``
        argument must be ``True`` so the return value is cached.  Internal
        calls set ``make_cache=False`` so memory isn't wasted for caching the
        triggered dependents of intermediate nodes.

        This private method can be used as a debugging tool to set values of
        non-input nodes.

        """
        if value == self._value:
            return set()
        self._value = value
        self._set_dependents_dirty()
        return self._get_triggered_dependents(make_cache=make_cache)

    def _evaluate(self):
        """Calculate the value for the Node

        Calls the action of the Node using values from the inputs of the Node.
        Returns the result of the action function.

        This function can also be overridden in subclasses if a class-based
        approach to creating Node actions is preferred.

        """
        if not self._action:
            raise NotImplementedError('You must define the action= argument '
                                      'when instantiating the Node')
        positional_values = [i.get_value()
                             for i in self._positional_inputs]
        keyword_values = {name: i.get_value()
                          for name, i in self._keyword_inputs.iteritems()}
        return self._action(*positional_values, **keyword_values)

    def _get_triggered_dependents(self, make_cache=True):
        """Return the set of triggered dependent nodes

        The set includes nodes which are marked as triggered and are included
        in the dependent chain from this node.

        The result is cached for the node if ``make_cache == True``, but
        caching is suppressed for recursively walked dependent nodes.  This way
        we only use cache memory only for nodes whose triggered dependents are
        queried from external code.

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
        """Paint all dependents dirty

        Paints direct dependents dirty, which causes recursive painting for the
        whole dependents tree.

        """
        for dependent in self._dependents:
            dependent._set_value(DIRTY, make_cache=False)

    def __unicode__(self):
        return unicode(self.get_value())

    def __repr__(self):
        return ('<{self.__class__.__name__} {self.name}: {self._value}>'
                .format(self=self))


def update_nodes_iter(nodes_and_values):
    """Update values of multiple nodes and trigger dependents

    This is a generator which iterates through the set of triggered dependent
    nodes.

    """
    triggered = set()
    for node, new_value in nodes_and_values:
        triggered |= node._set_value(new_value)
    for node in triggered:
        node.get_value()  # trigger evaluation
        yield node


def update_nodes(nodes_and_values):
    """Update values of multiple nodes and trigger dependents

    Use this variant of the ``update_nodes*`` functions if you don't need to
    access the set of triggered dependent nodes.

    """
    for _node in update_nodes_iter(nodes_and_values):
        pass


def update_nodes_get_triggered(nodes_and_values):
    """Update values of multiple nodes and trigger dependents

    This variant of the ``update_nodes*`` functions returns triggered
    dependents as a Python set.

    """
    return set(update_nodes_iter(nodes_and_values))
