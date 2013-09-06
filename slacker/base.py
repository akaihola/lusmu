import logging


log = logging.getLogger('slacker.base')


class DIRTY:
    pass


class Node(object):
    def __init__(self, name):
        self.name = name
        self._value = DIRTY
        self._dependents = set()

    def _evaluate(self):
        raise NotImplementedError('You must implement the _evaluate() method '
                                  'in subclasses of Node.')

    def get_value(self):
        if self._value is DIRTY:
            self._value = self._evaluate()
            log.debug('EVALUATED %s: %s', self.name, self._value)
            self._set_dependents_dirty()
        return self._value

    def set_value(self, value):
        if value != self._value:
            self._value = value
            self._set_dependents_dirty()

    def _set_dependents_dirty(self):
        for dependent in self._dependents:
            dependent.set_value(DIRTY)

    def connect(self, dependent):
        if dependent not in self._dependents:
            self._dependents.add(dependent)
            if self._value is not DIRTY:
                dependent.set_value(DIRTY)

    def __unicode__(self):
        return unicode(self.get_value())

    def __repr__(self):
        return ('<{self.__class__.__name__} {self._value}>'
                .format(self=self,
                        value=unicode(self).encode('ascii', errors='replace')))


