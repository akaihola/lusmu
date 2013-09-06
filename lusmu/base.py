import logging


log = logging.getLogger('lusmu.base')


_triggered_cache = {}


class DIRTY:
    pass


class Node(object):
    def __init__(self, name, triggered=False):
        """Initialize a node

        Arguments:
          name: the internal name of the node; used in the repr
          triggered: should this node be automatically evaluated when any of
                     its depended nodes changes value

        """
        self.name = name
        self._value = DIRTY
        self._dependents = set()
        self.triggered = triggered

    def connect(self, dependent):
        """Set the given node as a dependent of this node

        Immediately paints the new dependent dirty if this node has already
        been evaluated.

        Connecting nodes always invalidates the triggered nodes cache.

        """
        if dependent not in self._dependents:
            self._dependents.add(dependent)
            if self._value is not DIRTY:
                dependent.set_value(DIRTY, make_cache=False)
        _triggered_cache.clear()

    def get_value(self):
        """Return node value, evaluate if needed and paint dependents dirty"""
        if self._value is DIRTY:
            self._value = self._evaluate()
            log.debug('EVALUATED %s: %s', self.name, self._value)
            self._set_dependents_dirty()
        return self._value

    def set_value(self, value, make_cache=True):
        """Set a new value for this node

        If this caused the value to change, paints dependent nodes dirty and
        returns the set of those dependent nodes which are marked "triggered"
        and should be re-evaluated.

        When called from external code, the ``make_cache`` argument must be
        ``True`` so the return value is cached.  Internal calls set
        ``make_cache=False`` so memory isn't wasted for caching the triggered
        dependents of intermediate nodes.

        """
        if value == self._value:
            return set()
        self._value = value
        self._set_dependents_dirty()
        return self.get_triggered_dependents(make_cache=make_cache)

    def _evaluate(self):
        raise NotImplementedError('You must implement the _evaluate() method '
                                  'in subclasses of Node.')

    def get_triggered_dependents(self, make_cache=True):
        """Return the set of triggered dependent nodes

        The set includes nodes which are marked as triggered and are included
        in the dependent chain from this node.

        The result is cached for the node if ``make_cache == True``, but
        caching is suppressed for recursively walked dependent nodes.  This way
        we only use cache memory only for nodes whose triggered dependents are
        queried from external code.

        """
        if self in _triggered_cache:
            return _triggered_cache[self]
        triggered = set()
        for dependent in self._dependents:
            if dependent.triggered:
                triggered.add(dependent)
            triggered |= dependent.get_triggered_dependents(make_cache=False)
        if make_cache:
            _triggered_cache[self] = triggered
        return triggered

    def _set_dependents_dirty(self):
        """Paint all dependents dirty

        Paints direct dependents dirty, which causes recursive painting for the
        whole dependents tree.

        """
        for dependent in self._dependents:
            dependent.set_value(DIRTY, make_cache=False)

    def __unicode__(self):
        return unicode(self.get_value())

    def __repr__(self):
        return ('<{self.__class__.__name__} {self.name}: {self._value}>'
                .format(self=self,
                        value=unicode(self).encode('ascii', errors='replace')))


def update_nodes_iter(nodes_and_values):
    """Update values of multiple nodes and trigger dependents

    This is a generator which iterates through the set of triggered dependent
    nodes.

    """
    triggered = set()
    for node, new_value in nodes_and_values:
        triggered |= node.set_value(new_value)
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
