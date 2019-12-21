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


class UserDict(MutableMapping, AttributeDictMixin):
    """Dictionary-like data structure."""

    def __init__(self, data=None, **kwargs):
        _data = {}
        if data is not None:
            _data.update(data)
        _data.update(kwargs)
        self.__dict__.update(_data=_data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

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


class TreeNode:
    """Implementation of a vertex in a rooted tree.

    Instance of this class can be used as a leaf node or a branch node.
    """

    def __init__(self, value, **kwargs):
        self._value = value
        self._parent = None
        self._children = []

    def __str__(self):
        return str(self._value)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if isinstance(other, TreeNode):
            return self.get_value() == other.get_value()
        else:
            return self.get_value() == other

    def __contains__(self, other):
        try:
            self.index(other)
            return True
        except ValueError:
            return False

    def __getitem__(self, index):
        return self._children[index]

    def get_root(self):
        """Returns the root node."""
        parent = self.get_parent()
        return self if parent is None else parent.get_root()

    def get_children(self):
        return self._children

    def get_degree(self):
        """Returns number of children.

        A leaf node is necessarily degree zero.
        """
        return len(self._children)

    def get_depth(self):
        """Returns the number of edges along the shortest path between
        a node and the root.
        """
        parent = self.get_parent()
        if parent:
            return parent.get_depth() + 1
        else:
            return 0

    def get_path(self):
        """Returns a list of nodes connecting a node with the root."""
        parent = self.get_parent()
        path = [] if parent is None else parent.get_path()
        path.append(self)
        return path

    def get_parent(self):
        """
        Returns:
            :obj:`TreeNode`: The parent node, None if node is the root.
        """
        return self._parent

    def set_parent(self, parent):
        """Changes ancestory of the node."""
        self._parent = parent

    def get_value(self):
        return self._value

    def set_value(self, value):
        old_value = self._value
        self._value = value

    def index(self, node):
        """Returns first index of child node.

        Raises:
            ValueError: if the `node` is not present.
        """
        for index, child in enumerate(self._children):
            if node is child or node == child:
                return index
        else:
            raise ValueError('{0}({1!s}) have not got child {2}({3!s})'.format(
                type(self).__name__, self, type(node).__name__, node))

    def append(self, node):
        """Adds immediate descendant to a branch node.

        Raises:
            ValueError: if the node already has a child node with same value.
        """
        if node in self:
            raise ValueError('{0}({1!s}) already has child {2}({3!s})'.format(
                type(self).__name__, self, type(node).__name__, node))
        elif node.get_parent() is not None:
            node.get_parent().remove(node)
        node.set_parent(self)
        self._children.append(node)

    def remove(self, node):
        """Removes `node` from the list of child nodes.

        Returns:
            :obj:`TreeNode`: instance being removed.

        Raises:
            ValueError: if `node` is not present.
        """
        child = self._children.pop(self.index(node))
        child.set_parent(None)
        return child

    def has_children(self):
        return len(self._children) > 0

    def sort(self, key=None, reverse=False):
        """Recursive sorting of child nodes.

        Args:
            key (callable): a function that is used to extract a comparison key
                from each child node.
            reverse (boolean): If ``True`` then child nodes are sorted as
                if each comparison were reversed.
        """
        self._children.sort(key=key, reverse=reverse)
        for child in self._children:
            child.sort(key=key, reverse=reverse)

    def next_sibling(self):
        """Returns node's nearest sibling to the right."""
        parent = self.get_parent()
        index = None if parent is None else parent.index(self) + 1
        if index is None or index >= len(parent.get_children()):
            return None
        else:
            return parent[index]

    def prev_sibling(self):
        """Returns node's nearest sibling to the lest."""
        parent = self.get_parent()
        index = None if parent is None else parent.index(self) - 1
        if index is None or index < 0:
            return None
        else:
            return parent[index]

    children = property(lambda s: s.get_children(),
                        doc="A list of zero or more child nodes")
    degree = property(lambda s: s.get_degree(), doc="Number of children.")
    depth = property(lambda s: s.get_depth(),
                     doc="The distance between a node and the root.")
    parent = property(lambda s: s.get_parent(), lambda s: s.set_parent(),
                      doc="Reference to the parent node.")
    path = property(lambda s: s.get_path(),
                    doc="Path from the root to a node.")
    value = property(lambda s: s.get_value(), lambda s: s.set_value(),
                     doc="Data stored by the node.")


# vim: ts=4 sw=4 sts=4 et ai
