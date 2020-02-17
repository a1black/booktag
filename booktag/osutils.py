"""Functions for working with file system."""
import collections
import contextlib
import errno
import os
import re
import shutil
import stat

import magic
import psutil

from booktag import exceptions
from booktag.constants import AudioType, ImageType


class DirEntry:
    """
    Args:
        path (str): Full pathname.
    """

    def __init__(self, path):
        self._path = strippath(path)
        self._stat_cache = None

    def __str__(self):
        return self.path

    def __fspath__(self):
        return self.path

    def __eq__(self, other):
        return self.path == other

    def inode(self):
        return self.stat(follow_symlinks=False).st_ino

    def is_dir(self, *, follow_symlinks=True):
        return stat.S_ISDIR(self.stat(follow_symlinks=follow_symlinks).st_mode)

    def is_file(self, *, follow_symlinks=True):
        return stat.S_ISREG(self.stat(follow_symlinks=follow_symlinks).st_mode)

    def is_symlink(self):
        return stat.S_ISLNK(self.stat(follow_symlinks=False).st_mode)

    def stat(self, *, follow_symlinks=True):
        if self._stat_cache is None or self._stat_cache[1] != follow_symlinks:
            self._stat_cache = (
                os.stat(self.path, follow_symlinks=follow_symlinks),
                follow_symlinks)
        return self._stat_cache[0]

    @property
    def name(self):
        """str: Basename."""
        return os.path.split(self.path)[1]

    @property
    def parts(self):
        """tuple: Various parts of the path."""
        return pathparts(self.path)

    @property
    def path(self):
        """str: Pathname."""
        return self._path


class RecursiveScandirIterator(contextlib.AbstractContextManager):
    """Iterator that traverses directory using depth-first algorithm."""

    def __init__(self, path, *, follow_symlinks=True, maxdepth=None):
        path = DirEntry(path)
        self._follow_symlinks = follow_symlinks
        self._maxdepth = maxdepth
        self._depth_delta = len(path.parts)
        self._stack = collections.deque()
        if not path.is_dir(follow_symlinks=follow_symlinks):
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory',
                                     path.path)
        elif self._is_descendable(path):
            self._stack.append(os.scandir(path))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return exc_type is not None and issubclass(exc_type, StopIteration)

    def __iter__(self):
        return self

    def __next__(self):
        next_entry = self._pop_next_from_stack()
        if self._is_descendable(next_entry):
            self._stack.append(os.scandir(next_entry))
        return next_entry

    def is_descendable(self, entry):
        """Checks if iterator can descent into a directory."""
        depth = len(entry.parts) - self._depth_delta
        isdir = entry.is_dir(follow_symlinks=self._follow_symlinks)
        return isdir and (self._maxdepth is None or self._maxdepth > depth)

    def _pop_next_from_stack(self):
        """
        Returns:
            os.DirEntry: Next file entry determined by depth-first traversal
                algoritm.
        """
        try:
            current_iter = self._stack.pop()
            next_entry = next(current_iter)
            self._stack.append(current_iter)
            return next_entry
        except StopIteration:
            return self._pop_next_from_stack()
        except IndexError:
            raise StopIteration

    def close(self):
        """Closes scandir iterators stored in the stack."""
        while self._stack:
            self._stack.pop().close()


class Find(RecursiveScandirIterator):
    AUDIO_TYPE = 1
    IMAGE_TYPE = 2
    DIR_TYPE = 3

    def __init__(self, *args, type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = type

    def __next__(self):
        next_item = super().__next__()
        filetype = None if self._type is None else self._check_type(next_item)
        if self._type == filetype:
            return next_item
        else:
            return next(self)

    def _check_type(self, direntry):
        """
        Args:
            direntry (DirEntry): Pathname.

        Returns:
            int: File type.
        """
        try:
            filetype = file(direntry)
            if isinstance(filetype, AudioType):
                return self.AUDIO_TYPE
            elif isinstance(filetype, ImageType):
                return self.IMAGE_TYPE
            else:
                raise exceptions.FileTypeNotSupportedError(direntry)
        except IsADirectoryError:
            return self.DIR_TYPE
        except exceptions.FileTypeNotSupportedError:
            return None


def expandpath(path):
    """
    Args:
        path (os.PathLike): Path to be processed.

    Returns:
        str: Path with environment variables expanded.
    """
    return os.path.expanduser(os.path.expandvars(os.fsdecode(path)))


def absnormpath(path):
    """
    Args:
        path (os.PathLike): Path to process.
    Returns:
         str: Expanded absolute path.
     """
    return os.path.normcase(os.path.abspath(expandpath(path)))


def absrealpath(path):
    """Returns absolute canonical path."""
    return os.path.realpath(absnormpath(path))


def strippath(path):
    """
    Args:
        path: A pathname.

    Returns:
        list: Components of the pathname.
    """
    path = os.fsdecode(path)
    return path[0] + path[1:].rstrip(os.sep) if path else path


def pathparts(path):
    """Returns a tuple of path parts splited by the path separetor."""
    parts = []
    drive, path = os.path.splitdrive(strippath(path))
    base, name = os.path.split(path)
    while name:
        parts.insert(0, name)
        base, name = os.path.split(base)
    if base:
        parts.insert(0, base)
    if drive:
        parts.insert(0, drive)
    return tuple(parts)


def is_readable(path, stats=None, follow_symlinks=False):
    """
    Returns:
        bool: True if process has read permissions on the path.

    Raises:
        PermissionError: If check is failed.
    """
    if stats is None:
        stats = os.stat(path, follow_symlinks=follow_symlinks)
    if stat.S_ISREG(stats.st_mode) or stat.S_ISDIR(stats.st_mode):
        check_mode = os.R_OK
        mode = (stats.st_mode & 0o777) | stat.S_IREAD
        if not os.access(path, check_mode):
            try:
                os.chmod(path, mode, follow_symlinks=follow_symlinks)
            except PermissionError:
                raise PermissionError(
                    errno.EACCES, 'Permission denied', os.fspath(path))
    return True


def is_writable(path, stats=None, follow_symlinks=False):
    """
    Returns:
        bool: True if process has write permissions on the path.

    Raises:
        PermissionError: If check is failed.
    """
    if stats is None:
        stats = os.stat(path, follow_symlinks=follow_symlinks)
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
            os.chmod(path, mode, follow_symlinks=follow_symlinks)
        except PermissionError as error:
            raise PermissionError(
                errno.EACCES, 'Permission denied', os.fspath(path)) from error
    return True


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


def df(path):
    """
    Args:
        path (os.PathLike): Pathname to resolve system disk.

    Returns:
        int: Available space on a system disk.
    """
    memory = os.statvfs(path)
    return memory.f_frsize * memory.f_bfree


def free():
    """
    Returns:
        int: Available virtual memory.
    """
    memory = psutil.virtual_memory()
    return memory.available


def file(path):
    """Returns file type of the `path`.

    Raises:
        IsADirectoryError: If path is a directory.
        exceptions.FileTypeNotSupportedError: If file type not found in list of
            supported types.
    """
    try:
        mime = magic.from_file(os.fsdecode(path), mime=True)
    except IsADirectoryError:
        raise
    except OSError:
        filetype = None
    else:
        if re.match('^audio/(?:x-)?(?:mp[23]|mpeg)$', mime):
            filetype = AudioType.MP3
        elif re.match('^audio/(?:x-)?(?:m4a|mp4|mpeg4)$', mime):
            filetype = AudioType.MP4
        elif mime == 'audio/ogg':
            filetype = AudioType.OGG
        elif mime == 'image/jpeg':
            filetype = ImageType.JPEG
        elif mime == 'image/png':
            filetype = ImageType.PNG
        else:
            raise exceptions.FileTypeNotSupportedError(path)
    return filetype
