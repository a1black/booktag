from collections.abc import MutableMapping  # pylint: disable=import-error, no-name-in-module


class AttributeDictMixin:
    """Mixin adds attribute access to a dictionary-like object."""

    def __getattr__(self, key):
        """`d.key -> d[key]`."""
        try:
            return self[key]
        except KeyError:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(
                type(self).__name__, key))

    def __setattr__(self, key, value):
        """`d[key] = value -> d.key = value`."""
        self[key] = value

    def __delattr__(self, key):
        """`del d.key -> del d[key]`."""
        try:
            del self[key]
        except KeyError:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(
                type(self).__name__, key))


class attrdict(dict, AttributeDictMixin):
    """Dict with attribute access."""


class PropDict(MutableMapping, AttributeDictMixin):
    """Dictionary-like data structure.

    If value is ``callable`` object :meth:`.__getitem__` will invoke it.
    """

    def __init__(self, data=None, **kwargs):
        _data = {}
        if data is not None:
            _data.update(data)
        _data.update(kwargs)
        self.__dict__.update(_data=_data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        value = self._data[key]
        return value() if callable(value) else value

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, key):
        return key in self._data

    def clear(self):
        self._data.clear()

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class FiltrableDict(MutableMapping, AttributeDictMixin):
    """Dictionary-like structure where values converted to a given type."""

    def __init__(self, filters, **kwargs):
        if not isinstance(filters, dict):
            raise TypeError('{0}() expected filters be a dict, got {1}'.format(
                type(self).__name__, type(filters).__name__))
        self.__dict__.update(_data={}, _filters=filters)
        for key, value in kwargs.items():
            self[key] = value

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        try:
            if key in self._filters:
                self._data[key] = self._filters[key](value)
            else:
                self._data[key] = value
        except (TypeError, ValueError) as e:
            raise e.__class__('dict item {0!r}: {1}'.format(key, e)) from e

    def __delitem__(self, key):
        del self._data[key]

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls({})
        for key in iterable:
            d[key] = value
        return d


# vim: ts=4 sw=4 sts=4 et ai
