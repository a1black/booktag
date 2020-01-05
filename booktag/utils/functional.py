"""Functional style utilities."""
import functools
import os
import re


def len(iterable):
    """Returns length of `iterable`."""
    count = 0
    for _ in iterable:
        count += 1
    return count


def difference(base, *iterables):
    """Returns a list that contains the difference of two or more iterables."""
    if not len(iterables):
        raise TypeError("difference() missing 1 positional argument: "
                        "'iterables'")
    diff = []
    for item in base:
        for control in iterables:
            if item in control:
                break
        else:
            diff.append(item)
    return diff


def intersection(base, *iterables):
    """
    Returns a list that contains the intersection of two or more iterbales.
    """
    inter = []
    for item in base:
        for control in iterables:
            if item not in control:
                break
        else:
            inter.append(item)
    return inter


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


def not_decorator(func):
    """Returns wrapper function that negates result of `func`."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return not func(*args, **kwargs)

    return wrapper


def camel_to_snake(name):
    """Returns a string converted to snake case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(name):
    return ''.join(x.capitalize() for x in name.split('_'))


def str_shorten(data, maxlen, wrap='..'):
    """Returns a new string wrapped to length `maxlen`."""
    if len(data) <= abs(maxlen):
        shortend = data
    else:
        append = prepend = False
        wraplen = len(wrap)
        idx = slice(maxlen) if maxlen > 0 else slice(maxlen, len(data))
        if wraplen and wraplen < abs(maxlen):
            if maxlen > 0:
                append = True
                idx = slice(idx.start, idx.stop - wraplen)
            else:
                prepend = True
                idx = slice(idx.start + wraplen, idx.stop)
        shortend = wrap * prepend + data[idx] + wrap * append
    return shortend


# vim: ts=4 sw=4 sts=4 et ai
