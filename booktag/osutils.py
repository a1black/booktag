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

    def exists(self):
        return os.path.exists(self.path)

    def inode(self):
        return self.stat(follow_symlinks=False).st_ino

    def is_dir(self, *, follow_symlinks=True):
        return stat.S_ISDIR(self.stat(follow_symlinks=follow_symlinks).st_mode)

    def is_file(self, *, follow_symlinks=True):
        return stat.S_ISREG(self.stat(follow_symlinks=follow_symlinks).st_mode)

    def is_symlink(self):
        return stat.S_ISLNK(self.stat(follow_symlinks=False).st_mode)

    def size(self, *, follow_symlinks=True):
        stat_res = self.stat(follow_symlinks=follow_symlinks)
        return getattr(stat_res, 'st_size', 0)

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

    def _is_descendable(self, entry):
        """Checks if iterator can descent into a directory."""
        depth = len(entry.parts) - self._depth_delta
        isdir = entry.is_dir(follow_symlinks=self._follow_symlinks)
        return isdir and (self._maxdepth is None or self._maxdepth > depth)

    def _pop_next_from_stack(self):
        """
        Returns:
            DirEntry: Next file entry determined by depth-first traversal
                algoritm.
        """
        try:
            current_iter = self._stack.pop()
            next_entry = next(current_iter)
            self._stack.append(current_iter)
            return DirEntry(next_entry)
        except StopIteration:
            return self._pop_next_from_stack()
        except IndexError:
            raise StopIteration

    def close(self):
        """Closes scandir iterators stored in the stack."""
        while self._stack:
            self._stack.pop().close()

    @property
    def follow_symlinks(self):
        return self._follow_symlinks

    @property
    def maxdepth(self):
        return self._maxdepth


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


def chmod(path, *, read=True, write=True, follow_symlinks=True):
    """Changes the mode of `path` to make it writable and/or readable.

    Raises:
        PermissionError: If access permissions cannot be changed.
    """
    access_kw, chmow_kw = {}, {}
    if os.access in os.supports_follow_symlinks:
        access_kw['follow_symlinks'] = follow_symlinks
    if os.chmod in os.supports_follow_symlinks:
        chmow_kw['follow_symlinks'] = follow_symlinks
    stat_res = os.stat(path, follow_symlinks=follow_symlinks)
    access_mode = 0
    mode = stat_res.st_mode & 0o777
    if read:
        access_mode |= os.R_OK
        mode |= stat.S_IREAD
    if write:
        access_mode |= os.W_OK
        mode |= stat.S_IWRITE
        if stat.S_ISDIR(stat_res.st_mode):
            access_mode |= os.X_OK
            mode |= stat.S_IEXEC
    if not os.access(path, access_mode, **access_kw):
        try:
            os.chmod(path, mode, **chmow_kw)
        except PermissionError as error:
            raise PermissionError(
                errno.EACCES, 'Permission denied', os.fspath(path)) from error


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


def file(path, *, follow_symlinks=True):
    """Returns file type of the `path`.

    Raises:
        IsADirectoryError: If path is a directory.
        exceptions.FileTypeNotSupportedError: If file type not found in list of
            supported types.
    """
    try:
        if follow_symlinks:
            path = absrealpath(path)
        mime = magic.from_file(os.fsdecode(path), mime=True)
        ext = os.path.splitext(path)[1][1:].lower()
    except (IsADirectoryError, FileNotFoundError, PermissionError):
        raise
    except OSError:
        filetype = None
    else:
        if re.match('^audio/(?:x-)?(?:mp[23]|mpeg)$', mime):
            filetype = AudioType.MP3
        elif mime == 'application/octet-stream' and ext == 'mp3':
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


def is_audio(path, follow_symlinks=True):
    """Returns audio content type or False if not an audio file."""
    try:
        filetype = file(path, follow_symlinks=follow_symlinks)
        return filetype if isinstance(filetype, AudioType) else False
    except (IsADirectoryError, exceptions.FileTypeNotSupportedError):
        return False


def is_image(path, follow_symlinks=True):
    """Returns image content type or False if not an image file."""
    try:
        filetype = file(path, follow_symlinks=follow_symlinks)
        return filetype if isinstance(filetype, ImageType) else False
    except (IsADirectoryError, exceptions.FileTypeNotSupportedError):
        return False
