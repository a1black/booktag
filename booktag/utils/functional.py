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


def rstrip(iterable, function=None):
    """Returns a new list with tailing empty items removed.

    Function removes trailing items which `function(item)` is false.
    If ``function`` is None, removes items which evaluate to false.
    """
    values = list(iterable)
    for index in range(len(values) - 1, -1, -1):
        if function is None and values[index]:
            break
        elif function and function(values[index]):
            break
    else:
        index = -1
    return values[:index + 1]


def lstrip(iterable, function=None):
    """Returns a new list with leading empty items removed.

    Function removes leading items with `function(item)` is false.
    If ``function`` is None, removes items with evaluate to false.
    """
    values = list(iterable)
    for index, item in enumerate(values):
        if function is None and item:
            break
        elif function and function(item):
            break
    else:
        index = len(values)
    return iterable[index:]


# vim: ts=4 sw=4 sts=4 et ai
