class Node:
    """Implementation of a vertex in an undirected rooted tree.

    Instance of this class can be used as a leaf node or a branch node.
    """

    def __init__(self, value, **kwargs):
        self._value = value
        self._parent = None
        self._children = []
        self._sort_keys = {
            "value": lambda node: node.get_value(),
            "degree": lambda node: node.get_degree()
        }

    def __str__(self):
        return str(self._value)

    def __eq__(self, other):
        if isinstance(other, Node):
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

    def _resolve_sort_key(self, key):
        """Returns one of supported key function."""
        if key is None:
            key = self._sort_keys['value']
        elif isinstance(key, str):
            key = self._sort_keys.get(key)
            if key is None:
                raise ValueError('unknown key function {0!r}'.format(key))
        return key

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
            :obj:`Node`: The parent node, None if node is the root.
        """
        return self._parent

    def set_parent(self, parent):
        """Changes ancestory of the node."""
        self._parent = parent

    def get_value(self):
        return self._value

    def set_value(self, value):
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
            :obj:`Node`: instance being removed.

        Raises:
            ValueError: if `node` is not present.
        """
        child = self._children.pop(self.index(node))
        child.set_parent(None)
        return child

    def sort(self, key=None, reverse=False):
        """Sorts child nodes.

        Args:
            key (callable): a function that is used to extract a comparison key
                from each child node.
            reverse (boolean): If ``True`` then child nodes are sorted as
                if each comparison were reversed.
        """
        self._children.sort(key=self._resolve_sort_key(key), reverse=reverse)

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

    children = property(lambda s: s.get_children,
                        doc="A list of zero or more child nodes")
    degree = property(lambda s: s.get_degree, doc="Number of children.")
    depth = property(lambda s: s.get_depth,
                     doc="The distance between a node and the root.")
    parent = property(lambda s: s.get_parent, lambda s: s.set_parent,
                      doc="Reference to the parent node.")
    path = property(lambda s: s.get_path, doc="Path from the root to a node.")
    sort_keys = property(lambda s: list(s._sort_keys.keys()),
                         doc="Names of supported key functions.")
    value = property(lambda s: s.get_value, lambda s: s.set_value,
                     doc="Data stored by the node.")


# vim: ts=4 sw=4 sts=4 et ai
