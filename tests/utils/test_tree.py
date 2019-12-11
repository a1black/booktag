import unittest.mock as mock

import pytest

from booktag.utils import tree


@pytest.fixture
def maketree():
    """Returns function for generating dummy tree."""
    def recurmake(node, depth, width):
        for i in range(1, width + 1):
            current = tree.Node('value_{:02d}'.format(i))
            if depth > 0:
                recurmake(current, depth - 1, width)
            node.append(current)
        return node

    def builder(depth, width) -> tree.Node:
        root = tree.Node('root')
        return recurmake(root, depth - 1, width)

    return builder


@pytest.fixture
def makenode():
    """Returns function for generating dummy node."""
    def builder(value: str, *children):
        node = tree.Node(value)
        for child in children or []:
            node.append(tree.Node(child))
        return node

    return builder


class TestNode:

    def test_eq_where_nodes_compared_by_value_expect_True(self, makenode):
        base_value = 'node'
        node1, node2 = makenode(base_value), makenode(base_value)
        assert node1 == node2
        assert node1 == base_value

    def test_contains_where_node_searched_by_value_expect_True(self, makenode):
        base_value = 'child'
        node1, node2 = makenode('root', base_value), makenode(base_value)
        assert node2 in node1
        assert base_value in node1

    def test_append_where_node_has_parent_expect_change_of_ancestor(
            self, makenode):
        parent, child = makenode('parent'), makenode('child')
        newparent = makenode('newparent')
        parent.append(child)
        assert child.get_parent() is parent
        assert len(parent.get_children()) == 1
        with mock.patch.object(parent, 'remove') as mock_meth:
            newparent.append(child)
            mock_meth.assert_called_once_with(child)
            assert child.get_parent() is newparent
            assert len(newparent.get_children()) == 1

    def test_append_where_node_is_present_expect_ValueError(self, makenode):
        parent, child = makenode('parent', 'child'), makenode('child')
        with pytest.raises(ValueError):
            parent.append(child)

    def test_remove_where_node_not_present_expect_ValueError(self, makenode):
        parent, child = makenode('parent'), makenode('child')
        with pytest.raises(ValueError):
            parent.remove(child)

    def test_remove_expect_removed_child(self, makenode):
        parent, child = makenode('parent', 'child'), makenode('child')
        with mock.patch('booktag.utils.tree.Node.set_parent') as mock_meth:
            removed = parent.remove(child)
            mock_meth.assert_called_once_with(None)
            assert len(parent.get_children()) == 0

    def test_next_sibling_expect_node_on_the_right(self, makenode):
        parent = makenode('parent')
        child1, child2, child3 = makenode('1'), makenode('2'), makenode('3')
        parent.append(child1)
        parent.append(child2)
        parent.append(child3)
        assert parent.next_sibling() is None
        assert child1.next_sibling() is child2
        assert child2.next_sibling() is child3
        assert child3.next_sibling() is None

    def test_prev_sibling_expect_node_on_the_right(self, makenode):
        parent = makenode('parent')
        child1, child2, child3 = makenode(1), makenode(2), makenode(3)
        parent.append(child1)
        parent.append(child2)
        parent.append(child3)
        assert parent.prev_sibling() is None
        assert child1.prev_sibling() is None
        assert child2.prev_sibling() is child1
        assert child3.prev_sibling() is child2

    def test_sort_where_sort_by_supported_key_function(self, makenode):
        root = makenode('root', 3, 2, 1)
        value, degree = mock.Mock(return_value=1), mock.Mock(return_value=1)
        with mock.patch.dict(root._sort_keys,
                             {'value': value, 'degree': degree}):
            root.sort()
            root.sort(key='degree')
            assert value.call_count == root.get_degree()
            assert degree.call_count == root.get_degree()

    def test_get_path_expect_list_of_nodes(self, makenode):
        root = makenode('root', 1, 2, 3)
        path = root[0].get_path()
        assert len(path) == 2
        assert path[0] is root
        assert path[1] is root[0]

    def test_get_depth_expect_integer(self, makenode):
        root = makenode('root', 1, 2, 3)
        assert root.get_depth() == 0
        assert root[0].get_depth() == 1


# vim: ts=4 sw=4 sts=4 et ai
