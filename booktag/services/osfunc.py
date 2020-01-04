import errno
import os
import shutil
import stat


class DirInfo:
    """
    Args:
        path (str): Full pathname.
        stat (:class:`os.stat_result`): File attributes.

    Attributes:
        name (str): The entry's base filename.
        path (str): The entry's full pathname.
        parent (str): The entry's parent pathname.
    """

    def __init__(self, path, stat):
        self.path = os.fspath(path)
        self.parent, self.name = os.path.split(path)
        self.stat = stat

    def __str__(self):
        return self.path

    def __fspath__(self):
        return self.path

    def __eq__(self, other):
        return self.path == other

    def is_dir(self, **kwargs):
        return stat.S_ISDIR(self.stat.st_mode)

    def is_file(self, **kwargs):
        return stat.S_ISREG(self.stat.st_mode)

    def is_symlink(self, **kwargs):
        return stat.S_ISLNK(self.stat.st_mode)

    @classmethod
    def from_path(cls, path):
        return cls(path, os.stat(path, follow_symlinks=False))

    @classmethod
    def from_entry(cls, entry):
        return cls(entry.path, entry.stat(follow_symlinks=False))

    @classmethod
    def make_from(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, os.DirEntry):
            return cls.from_entry(obj)
        else:
            return cls.from_path(obj)


def absnormpath(path):
    """Returns expanded absolute path."""
    expanded = os.path.expanduser(os.path.expandvars(path))
    return os.path.normcase(os.path.abspath(expanded))


def absrealpath(path):
    """Returns absolute canonical path."""
    return os.path.realpath(absnormpath(path))


def is_readable(path, stats=None):
    """Tests readability of `path`.

    Raises:
        PermissionError: If check is failed.
    """
    if stats is None:
        stats = os.stat(path, follow_symlinks=False)
    if stat.S_ISREG(stats.st_mode) or stat.S_ISDIR(stats.st_mode):
        check_mode = os.R_OK
        mode = (stats.st_mode & 0o777) | stat.S_IREAD
        if not os.access(path, check_mode):
            try:
                os.chmod(path, mode, follow_symlinks=False)
            except PermissionError:
                raise PermissionError(
                    errno.EACCES, 'Permission denied', os.fspath(path))
    return True


def is_writable(path, stats=None):
    """Tests writability of `path`.

    Raises:
        PermissionError: If check is failed.
    """
    if stats is None:
        stats = os.stat(path, follow_symlinks=False)
    if stat.S_ISDIR(stats.st_mode):
        check_mode = os.W_OK | os.X_OK
        mode = (stats.st_mode & 0o777) | stat.S_IWRITE | stat.S_IEXEC
    elif stat.S_ISREG(stats.st_mode):
        check_mode = os.W_OK
        mode = (stats.st_mode & 0o777) | stat.S_IWRITE
    else:
        return True
    if not os.access(path, check_mode):
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except PermissionError:
            raise PermissionError(
                errno.EACCES, 'Permission denied', os.fspath(path))
    return True


def recursive_listdir(path, *, maxdepth=None):
    """File tree exploration algoritm with start point at the `path`.

    Function explore tree in *depth-first* manner.
    Function does not explore symbole links that point to a directory.

    Args:
        path (str): A pathname.
        maxdepth(:obj:`int`, optional): Number of levels to descend.

    Yields:
        str: The file's full path name.
    """
    yield path  # yield current path
    if maxdepth is None or maxdepth > 0:
        if os.path.isdir(path) and not os.path.islink(path):
            depth = None if maxdepth is None else maxdepth - 1
            for filename in os.listdir(path):
                yield from recursive_listdir(os.path.join(path, filename),
                                             maxdepth=depth)


def recursive_scandir(path, *, maxdepth=None):
    """File tree exploration algoritm with start point at the `path`.

    Function explore tree in *depth-first* manner.
    Function does not explore symbole links that point to a directory.

    Args:
        path (str): A pathname.
        maxdepth(:obj:`int`, optional): Number of levels to descend.

    Yields:
        :class:`DirInfo`: Object corresponding to the file entry.
    """

    path = DirInfo.make_from(path)
    yield path
    if maxdepth is None or maxdepth > 0:
        if path.is_dir():
            with os.scandir(path) as curpath:
                depth = None if maxdepth is None else maxdepth - 1
                for entry in curpath:
                    yield from recursive_scandir(entry, maxdepth=depth)


def rename(path, new_name):
    """Changes name of the file or directory to `new_name`.

    Args:
        path (str): A pathname.
        new_name (str): The new base name of pathname `path`.

    Raises:
        FileExistsError: If a file or directory with such name already exists.
    """
    if os.path.basename(new_name) != new_name:
        raise ValueError('rename() expected second argument to be basename '
                         'not pathname: {0}'.format(new_name))
    dst = os.path.join(os.path.dirname(path), new_name)
    if os.path.exists(dst):
        raise FileExistsError(errno.EEXIST, 'File exists', dst)
    os.rename(path, dst)


def remove(path):
    """Removes the file `path`.

    If `path` points to a directory then an entire directory tree is deleted.
    """
    def retry_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        os.remove(path)
    except IsADirectoryError:
        shutil.rmtree(path, onerror=retry_readonly)


# vim: ts=4 sw=4 sts=4 et ai
