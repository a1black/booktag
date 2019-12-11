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
