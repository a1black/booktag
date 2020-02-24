import collections
import contextlib
import errno
import re

import natsort

from booktag import osutils


# Type filtering constants
DIR_TYPE = 'd'
FILE_TYPE = 'f'
SYMLINK_TYPE = 's'
AUDIO_TYPE = 'a'
IMAGE_TYPE = 'i'
# File sorting constants
NUMERIC_SORT = 'numeric'
NAT_SORT = 'natsort'


def _isdir(entry, follow_symlinks=True, **kwargs):
    return entry.is_dir(follow_symlinks=follow_symlinks)


def _isfile(entry, follow_symlinks=True, **kwargs):
    return entry.is_file(follow_symlinks=follow_symlinks)


def _issymlink(entry, **kwargs):
    return entry.is_symlink()


class FindIter(contextlib.AbstractContextManager):
    """Recursive directory iteractor that support file selection criterias."""

    def __init__(self, path, **kwargs):
        self._follow_symlinks = kwargs.get('follow_symlinks', True)
        self._maxdepth = kwargs.get('maxdepth', None)
        self._root = osutils.DirEntry(path)
        if not self._root.is_dir(follow_symlinks=self.follow_symlinks):
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', path)
        self._iter = None
        self._filters = []
        self._exec = None
        self._name_regexp = None
        self._perm = 0

    def __iter__(self):
        if self._iter is None:
            self._init_iter()
        return self

    def __enter__(self):
        if self._iter is None:
            self._init_iter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._iter.close()
        return exc_type is not None and issubclass(exc_type, StopIteration)

    def __next__(self):
        next_item = next(self._iter)
        self._set_perms(next_item)
        if self._validate_name(next_item) and self._validate_type(next_item):
            return self._exec_command(next_item)
        else:
            return next(self)

    def _exec_command(self, entry):
        return entry if self._exec is None else self._exec(entry)

    def _init_iter(self):
        self._set_perms(self._root)
        self._iter = osutils.RecursiveScandirIterator(
            self._root, follow_symlinks=self.follow_symlinks,
            maxdepth=self._maxdepth)

    def _validate_name(self, entry):
        return not self._name_regexp or self._name_regexp.search(entry.name)

    def _validate_type(self, entry):
        for filter_obj, negate in self._filters:
            result = filter_obj(entry, follow_symlinks=self.follow_symlinks)
            result = not result if negate else result
            if not result:
                return False
        return True

    def _set_perms(self, entry):
        if self._perm:
            osutils.chmod(
                entry, read='r' in self._perm, write='w' in self._perm,
                follow_symlinks=self.follow_symlinks)

    def exec(self, function):
        """Sets callable object that applied to find file."""
        if not callable(function):
            raise TypeError('exec() expected callable object, got: {0}'.format(
                type(function).__name__))
        self._exec = function
        return self

    def name(self, exp, *, ignorecase=False):
        """Sets regular expression for matching file basename."""
        try:
            self._name_regexp = re.compile(exp, flags=re.I * ignorecase)
        except re.error as error:
            raise ValueError(
                'Invalid file name pattern: {0}'.format(exp)) from error
        return self

    def perm(self, mode):
        """Sets file permission mode.

        Args:
            mode (str): Access mode - 'r', 'w' or 'rw'.
        """
        try:
            self._perm = ''.join(sorted(mode)).lower() if mode else None
            if self._perm not in ('r', 'w', 'rw'):
                raise ValueError('invalid mode: {0!r}'.format(mode))
        except TypeError:
            raise TypeError(
                'expected str, not {0}'.format(type(mode).__name__))
        return self

    def type(self, type_, *andtype, negation=False):
        """Sets file type filter."""
        for type_ in (type_,) + andtype:
            if type_ == DIR_TYPE:
                self._filters.append((_isdir, negation))
            elif type_ == FILE_TYPE:
                self._filters.append((_isfile, negation))
            elif type_ == SYMLINK_TYPE:
                self._filters.append((_issymlink, negation))
            elif type_ == AUDIO_TYPE:
                self._filters.append((osutils.is_audio, negation))
            elif type_ == IMAGE_TYPE:
                self._filters.append((osutils.is_image, negation))
            elif type_ is None:
                self._filters.clear()
            else:
                raise ValueError('Unknown type modifier: {0}'.format(type_))
        return self

    @property
    def follow_symlinks(self):
        """bool: If True descend into directories refered by symbolic link."""
        return self._follow_symlinks

    @property
    def maxdepth(self):
        """int: Maximum number of directories to descend, read-only."""
        return self._maxdepth


class FindStatic(FindIter):
    """
    Recursive directory iterator that loads and sorts directory entries before
    yielding onces that satisfies selection criterias.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_handler = kwargs.get('error_handler', None)
        self._sort = None
        self._len = 0

    def __len__(self):
        return self._len

    def __next__(self):
        return next(self._iter)

    def _init_iter(self):
        files = []
        buffer = collections.deque([self._root])
        while buffer:
            current = buffer.pop()
            self._set_perms(current)
            try:
                entries = list(osutils.RecursiveScandirIterator(
                    current, maxdepth=1, follow_symlinks=self.follow_symlinks))
                if self._sort is not None:
                    entries.sort(key=self._sort[0], reverse=not self._sort[1])
                buffer.extend(entries)
            except NotADirectoryError:
                pass
            if self._validate_name(current) and self._validate_type(current):
                files.append(self._exec_command(current))
        self._len = len(files)
        self._iter = iter(files)

    def sort(self, sorting, *, reverse=False):
        """Sets method for sorting directory entries."""
        if sorting == NUMERIC_SORT:
            self._sort = (lambda entry: entry.name, reverse)
        elif sorting == NAT_SORT:
            self._sort = (natsort.natsort_keygen(key=lambda entry: entry.name),
                          reverse)
        else:
            raise ValueError('Unknown sorting method: {0}'.format(sorting))
        return self
