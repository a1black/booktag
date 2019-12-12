import os
import stat
import tempfile
import unittest.mock as mock

import pyfakefs
import pytest

from booktag import exceptions
from booktag.service import scan
from booktag.utils import ftstat


def fakefile(fs, path, perm):
    """Creates file in mocked file system.

    Args:
        fs: Fake file system.
        path: The absolute path to the file to create.
        perm: The permission bits as set by `chmod`.
    """
    fs.create_file(path, st_mode=stat.S_IFREG | perm, create_missing_dirs=True)


def fakedir(fs, path, perm, size):
    """Creates a directory with files.

    Args:
        fs: Fake file system.
        path: The full directory path to create.
        perm: The permission bits as set by `chmod`.
        size: Number of files in the directory.
    """
    fs.create_dir(path, perm)
    while size > 0:
        fakefile(fs, os.path.join(path, str(size)), perm)
        size -= 1


def fakesymlink(fs, path):
    """Creates a regular file and a symbol link to that file.

    Args:
        fs: Fake file system.
        path: The full path to the symbol link to create.
    """
    filepath = os.path.join(os.path.dirname(path), 'file')
    fs.create_file(filepath, create_missing_dirs=True)
    fs.create_symlink(path, filepath)


@pytest.fixture
def fs_file(fs):
    """Fixture for creating single fake file."""
    return lambda *args, **kwargs: fakefile(fs, *args, **kwargs)


@pytest.fixture
def fs_dir(fs):
    """Fixture for creating single directory with `size` number of files."""
    return lambda *args, **kwargs: fakedir(fs, *args, **kwargs)


def test_recursive_iterdir_where_no_read_perm_for_file_expect_PermissionError(
        fs_file):
    path, perm = '/file/perm_-wx-wx-wx', 0o333
    with pytest.raises(PermissionError):
        fs_file(path, perm)
        with mock.patch('os.path.isfile', return_value=True):
            next(scan.recursive_iterdir(path))


def test_recursive_iterdir_where_no_write_perm_for_file_expect_PermissionError(
        fs_file):
    path, perm = '/file/perm_r-xr-xr-x', 0o555
    with pytest.raises(PermissionError):
        fs_file(path, perm)
        with mock.patch('os.path.isfile', return_value=True):
            with mock.patch('magic.from_file', return_value='audio/mp3'):
                next(scan.recursive_iterdir(path))


def test_recursive_iterdir_where_no_read_perm_for_dir_expect_PermissionError(
        fs_dir):
    path, perm, size = '/dir/perm_-wx-wx-wx', 0o333, 0
    with pytest.raises(PermissionError):
        fs_dir(path, perm, size)
        with mock.patch('os.path.isdir', return_value=True):
            next(scan.recursive_iterdir(path))


def test_recursive_iterdir_where_no_write_perm_for_dir_expect_PermissionError(
        fs_dir):
    path, perm, size = '/dir/perm_r-xr-xr-x', 0o555, 0
    with pytest.raises(PermissionError):
        fs_dir(path, perm, size)
        with mock.patch('os.path.isdir', return_value=True):
            next(scan.recursive_iterdir(path))


def test_recursive_iterdir_where_no_exec_perm_for_dir_expect_PermissionError(
        fs_dir):
    path, perm, size = '/dir/perm_rw-rw-rw-', 0o666, 0
    with pytest.raises(PermissionError):
        fs_dir(path, perm, size)
        with mock.patch('os.path.isdir', return_value=True):
            next(scan.recursive_iterdir(path))


def test_recursive_iterdir_where_not_dir_file_expect_FileNotSupportedError():
    with pytest.raises(exceptions.FileNotSupportedError):
        with mock.patch('booktag.utils.ftstat.ft_mode', return_value=0):
            next(scan.recursive_iterdir('non/existing/device'))


def test_recursive_iterdir_where_path_is_file_expect_yield_once(fs_file):
    path, perm = '/file', 0o777
    fs_file(path, perm)
    files = list(scan.recursive_iterdir(path))
    assert len(files) == 1
    assert files[0] == path


def test_recursive_iterdir_where_path_is_directory(fs_dir):
    root, perm, size = '/root/dir', 0o777, 10
    subdir = os.path.join(root, 'subdir')
    fs_dir(root, perm, size)
    fs_dir(subdir, perm, size)
    files = list(scan.recursive_iterdir(root))
    assert len(files) == 2 * (size + 1)
    assert files[0] == root
    assert subdir in files


def test_recursive_iterdir_where_traversal_depth_is_limited(fs_dir):
    root, perm, size = '/root', 0o777, 2
    depth1 = os.path.join(root, 'subdir')
    depth2 = os.path.join(depth1, 'subdir1')
    another_depth2 = os.path.join(depth1, 'subdir2')
    fs_dir(depth1, perm, size)
    fs_dir(depth2, perm, size)
    fs_dir(another_depth2, perm, size)
    # Test maxdepth = 0
    files = list(scan.recursive_iterdir(root, maxdepth=0))
    assert len(files) == 1
    assert files == [root]
    # Test maxdepth = 1
    files = list(scan.recursive_iterdir(root, maxdepth=1))
    assert len(files) == 2
    assert files == [root, depth1]
    # Test maxdepth = 2
    files = list(scan.recursive_iterdir(root, maxdepth=2))
    assert len(files) == 4 + size
    assert depth2 in files
    assert another_depth2 in files
    # Test maxdepth = 3
    files = list(scan.recursive_iterdir(root, maxdepth=3))
    assert len(files) == 4 + size * 3
    assert depth2 in files
    assert another_depth2 in files
    depth2_next_item = files[files.index(depth2) + 1]
    another_depth2_next_item = files[files.index(another_depth2) + 1]
    assert os.path.split(depth2_next_item)[0] == depth2  # child before sibling
    assert os.path.split(another_depth2_next_item)[0] == another_depth2
    # Test maxdepth = 4
    files = list(scan.recursive_iterdir(root, maxdepth=4))
    assert len(files) == 4 + size * 3


def test_path_scan_where_path_is_symlink_expect_IsASymlinkError(
        fs_file):
    path, perm = '/file/is/symlink', 0o776
    with pytest.raises(exceptions.IsASymlinkError):
        with mock.patch('booktag.utils.ftstat.ft_mode',
                        return_value=ftstat.S_IFLNK):
            fs_file(path, perm)
            next(scan.path_scan(path))


def test_path_scan_where_path_is_directory_expect_rooted_tree(fs_dir):
    root, root_size = '/root', 0
    branch1_name, branch2_name = 'branch1', 'branch2'
    branch1, branch1_size = os.path.join(root, branch1_name), 2
    branch2, branch2_size = os.path.join(root, branch2_name), 3
    fs_dir(root, 0o777, root_size)
    fs_dir(branch1, 0o777, branch1_size)
    fs_dir(branch2, 0o777, branch2_size)
    tree = scan.path_scan(root)
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
