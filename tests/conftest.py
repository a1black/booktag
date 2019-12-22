import os
import stat

import pyfakefs
import pytest


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


@pytest.fixture
def fs_file(fs):
    """Fixture for creating single fake file."""
    return lambda *args, **kwargs: fakefile(fs, *args, **kwargs)


@pytest.fixture
def fs_dir(fs):
    """Fixture for creating single directory with `size` number of files."""
    return lambda *args, **kwargs: fakedir(fs, *args, **kwargs)
