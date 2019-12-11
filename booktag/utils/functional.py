"""Functional style utilities."""
import functools
import os


def absnormpath(path):
    """Returns expanded absolute path."""
    expanded = os.path.expanduser(os.path.expandvars(path))
    return os.path.normcase(os.path.abspath(expanded))


def absrealpath(path):
    """Returns absolute canonical path."""
    return os.path.realpath(absnormpath(path))


def absnormpath_decr(func):
    """Decorator that expand and transforms first argument to absolute path."""

    @functools.wraps(func)
    def wrapper(path, *args, **kwargs):
        return func(absnormpath(path), *args, **kwargs)

    return wrapper
