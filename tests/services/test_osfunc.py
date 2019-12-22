import os
import stat
import unittest.mock as mock

import pytest

from booktag.services import osfunc


def test_rename_where_new_name_is_occupied_expect_FileExistsError(fs_file):
    oldname, newname = '/file/oldname', '/file/newname'
    with pytest.raises(FileExistsError):
        fs_file(oldname, 0o777)
        fs_file(newname, 0o777)
        osfunc.rename(oldname, os.path.split(newname)[1])


def test_rename_where_new_name_is_path_expect_ValueError():
    with pytest.raises(ValueError):
        osfunc.rename('/file/oldname', '/file/newname')


def test_is_writable_where_file_is_writable_expect_no_change_in_mode(fs_file):
    path, perm = '/file/perm_rw-rw-rw-', 0o666
    fs_file(path, perm)
    assert osfunc.is_writable(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == perm


def test_is_writable_where_file_not_writable_expect_change_in_mode(fs_file):
    path, perm = '/file/perm_r--r--r--', 0o444
    fs_file(path, perm)
    assert osfunc.is_writable(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o644


def test_is_writable_where_dir_is_writable_expect_no_change_in_mode(fs_dir):
    path, perm = '/dir/perm_rwxrwxrwx', 0o777
    fs_dir(path, perm, 0)
    assert osfunc.is_writable(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == perm


def test_is_writable_where_dir_not_writable_expect_change_in_mode(fs_dir):
    path, perm = '/dir/perm_r--r--r--', 0o444
    fs_dir(path, perm, 0)
    assert osfunc.is_writable(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o744


@pytest.mark.parametrize('method', ['recursive_listdir', 'recursive_scandir'])
def test_explore_path_methods_where_path_is_file_expect_yield_once(
        fs_file, method):
    recursion = getattr(osfunc, method)
    path, perm = '/file', 0o777
    fs_file(path, perm)
    files = list(recursion(path))
    assert len(files) == 1
    assert files[0] == path


@pytest.mark.parametrize('method', ['recursive_listdir', 'recursive_scandir'])
def test_explore_path_methods_where_directory_expect_path_and_its_content(
        fs_dir, method):
    recursion = getattr(osfunc, method)
    root, perm, size = '/root/dir', 0o777, 10
    subdir = os.path.join(root, 'subdir')
    fs_dir(root, perm, size)
    fs_dir(subdir, perm, size)
    files = list(recursion(root))
    assert len(files) == 2 * (size + 1)
    assert files[0] == root
    assert subdir in files


@pytest.mark.parametrize('method', ['recursive_listdir', 'recursive_scandir'])
def test_explore_path_methods_where_traversal_depth_is_limited(fs_dir, method):
    recursion = getattr(osfunc, method)
    root, perm, size = '/root', 0o777, 2
    depth1 = os.path.join(root, 'subdir')
    depth2 = os.path.join(depth1, 'subdir1')
    another_depth2 = os.path.join(depth1, 'subdir2')
    fs_dir(depth1, perm, size)
    fs_dir(depth2, perm, size)
    fs_dir(another_depth2, perm, size)
    # Test maxdepth = 0
    files = list(recursion(root, maxdepth=0))
    assert len(files) == 1
    assert files == [root]
    # Test maxdepth = 1
    files = list(recursion(root, maxdepth=1))
    assert len(files) == 2
    assert files == [root, depth1]
    # Test maxdepth = 2
    files = list(recursion(root, maxdepth=2))
    assert len(files) == 4 + size
    assert depth2 in files
    assert another_depth2 in files
    # Test maxdepth = 3
    files = list(recursion(root, maxdepth=3))
    assert len(files) == 4 + size * 3
    assert depth2 in files
    assert another_depth2 in files
    depth2_next_item = files[files.index(depth2) + 1]
    another_depth2_next_item = files[files.index(another_depth2) + 1]
    assert os.path.split(depth2_next_item)[0] == depth2  # child before sibling
    assert os.path.split(another_depth2_next_item)[0] == another_depth2
    # Test maxdepth = 4
    files = list(recursion(root, maxdepth=4))
    assert len(files) == 4 + size * 3
