import weakref


class ChainMixin:
    """Interface for implementing *Chain of Responsibility* pattern."""

    def getnext(self):
        """Returns next link in the chain."""
        return getattr(self, '_chain_next', None)

    def setnext(self, next_link):
        """Adds new link to the end of the chain."""
        follow = self.getnext()
        if follow is None:
            self._chain_next = next_link
        else:
            follow.setnext(next_link)


class Observer:
    """Interface for implementing *Observer* pattern."""

    def __call__(self, *args, **kwargs):
        return self.listen_observable(*args, **kwargs)

    def _subscribe_to_observable(self, subject):
        if isinstance(subject, Observable):
            subject.attach_observer(self)

    def listen_observable(self, subject, event, *args, **kwargs):
        raise NotImplementedError


class Observable:
    """Implementation of the *Subject* in *Observer* pattern.

    Subject holds weak references to the observers.

    Class must be used with caution or process will stuck in an infinite loop.
    To avoid this problem all registred *observers* must be fairly simple and
    do not modify *subject*.

    TODO:
        * Add logging for unhandled exceptions.
        * Add thread safety.
    """
    _observers = None

    def _index_of_observer(self, observer):
        """Returns an index of `observer`, or ``-1`` if not found."""
        if self._observers is None:
            self._observers = []
        for index, ref in enumerate(self._observers):
            if ref() == observer:
                return index
        return -1

    def attach_observer(self, observer):
        """Adds callable object to a list of observers."""
        if self._index_of_observer(observer) < 0:
            try:
                ref = weakref.WeakMethod(observer)
            except TypeError:
                ref = weakref.ref(observer)
            self._observers.append(ref)

    def detach_observer(self, observer):
        """Removes `observer` from the list of observers."""
        index = self._index_of_observer(observer)
        if index >= 0:
            self._observers.pop(index)

    def notify_observers(self, event, *args, **kwargs):
        """Notifies registred observers."""
        observers = [] if self._observers is None else self._observers
        self._observers = [x for x in observers if x() is not None]
        for ref in self._observers:
            try:
                ref()(self, event, *args, **kwargs)
            except TypeError:
                # If garbage was collected and we end up with dead ref.
                if ref() is not None:
                    raise


# vim: ts=4 sw=4 sts=4 et ai
