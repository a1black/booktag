import os
import stat
import unittest.mock as mock

import pyfakefs
import pytest

from booktag.services import treefunc


def test_map_tree():
    mock_f1 = mock.MagicMock(return_value='f1')
    mock_f2 = mock.MagicMock(return_value='f2')
    mock_f3 = mock.MagicMock(return_value='f3')
    result = list(treefunc.map_tree(['initial'], mock_f1, mock_f2, mock_f3))
    assert result == ['f3']
    mock_f1.assert_called_once_with('initial')
    mock_f2.assert_called_once_with('f1')
    mock_f3.assert_called_once_with('f2')


def test_filter_tree_where_funcs_return_True_expect_item():
    data = ['initial']
    mock_f1 = mock.MagicMock(return_value=True)
    mock_f2 = mock.MagicMock(return_value=True)
    mock_f3 = mock.MagicMock(return_value=True)
    result = list(treefunc.filter_tree(data, mock_f1, mock_f2, mock_f3))
    assert result == data
    mock_f1.assert_called_once_with('initial')
    mock_f2.assert_called_once_with('initial')
    mock_f3.assert_called_once_with('initial')


def test_filter_tree_where_funcs_return_False_expect_empty_iter():
    data = ['initial']
    mock_f1 = mock.MagicMock(return_value=False)
    mock_f2 = mock.MagicMock(return_value=False)
    mock_f3 = mock.MagicMock(return_value=False)
    result = list(treefunc.filter_tree(data, mock_f1, mock_f2, mock_f3))
    assert not result
    mock_f1.assert_called_once_with('initial')
    mock_f2.assert_not_called()
    mock_f3.assert_not_called()


def test_build_filetree_where_path_is_directory_expect_rooted_tree(fs_dir):
    root, root_size = '/root', 0
    branch1_name, branch2_name = 'branch1', 'branch2'
    branch1, branch1_size = os.path.join(root, branch1_name), 2
    branch2, branch2_size = os.path.join(root, branch2_name), 3
    fs_dir(root, 0o777, root_size)
    fs_dir(branch1, 0o777, branch1_size)
    fs_dir(branch2, 0o777, branch2_size)
    tree = treefunc.build_filetree(root)
    # Check tree root
    assert tree.get_value() == root
    assert len(tree.get_children()) == 2
    assert branch1_name in tree
    assert branch2_name in tree
    # Check branch1
    branch1_node = tree[tree.index(branch1_name)]
    assert branch1_node.get_parent() is tree
    assert branch1_node.get_value() == branch1_name
    assert len(branch1_node.get_children()) == branch1_size
    # Check branch2
    branch2_node = tree[tree.index(branch2_name)]
    assert branch2_node.get_parent() is tree
    assert branch2_node.get_value() == branch2_name
    assert len(branch2_node.get_children()) == branch2_size
    # Check path resolution
    for child in branch1_node.get_children():
        assert os.path.exists(child)
    for child in branch2_node.get_children():
        assert os.path.exists(child)
