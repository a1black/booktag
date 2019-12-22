import os

from booktag.utils import behavioral
from booktag.utils import collections


class AggregatorProp:
    """Class descend file node and accumulate values of child nodes.

    Args:
        *props: List o property names.
    """
    def __init__(self, *props):
        self._props = props

    def __call__(self, prop_container):
        """
        Args:
            prop_container: Mapping that contains this property.
        """
        agg_value = 0
        node = getattr(prop_container, 'container', None)
        if node and node.has_children():
            for child in node.get_children():
                for prop in self._props:
                    agg_value += getattr(child, prop, 0)
        return agg_value


class PropDict(collections.UserDict):
    """Dictionary-like data structure.

    If value is ``callable`` object :meth:`.__getitem__` will invoke it.
    """
    def __init__(self, container, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(container=container)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        return value(self) if callable(value) else value


class FileNode(collections.TreeNode, os.PathLike, behavioral.Observable):
    """Vertex that implements :class:`os.PathLike` interface."""

    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)
        self._props = PropDict(self, kwargs)

    def __fspath__(self):
        return os.path.join(*(x.get_value() for x in self.get_path()))

    def __getattr__(self, name):
        try:
            return self.props[name]
        except KeyError:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(
                type(self).__name__, name))

    def get_props(self):
        return self._props

    def set_value(self, value):
        old_value = self.get_value()
        super().set_value(value)
        # Event: ('update_value', old_value).
        self.notify_observers('update_value', old_value)

    def append(self, node):
        if node.get_parent() is None:
            parent, name = os.path.split(node.get_value())
            if parent != os.fspath(self):
                raise ValueError("'{0}' can't be parent of '{1}'".format(
                    os.fspath(self), node.get_value()))
            node.set_value(name)
        super().append(node)
        # Event: ('add_child', new_child)
        self.notify_observers('add_child', node)

    def remove(self, node):
        child = super().remove(node)
        # Event: ('remove_child', removed_child)
        self.notify_observers('removed_child', child)
        return child

    props = property(lambda s: s.get_props(), doc="File properties.")


# vim: ts=4 sw=4 sts=4 et ai
