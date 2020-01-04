import os

import natsort

from booktag import exceptions
from booktag.app import filenode
from booktag.app import tagcontainer
from booktag.services import osfunc
from booktag.utils import ftstat
from booktag.utils import functional


def _make_filenode(entry):
    """Returns a new instance of node in the file tree."""
    st_size = getattr(entry.stat, 'st_size', 0)
    ft_mode = ftstat.ft_mode(entry.path, entry.stat)
    if ftstat.S_IFMT(ft_mode) == 0:
        raise exceptions.NotDirectoryOrFileError(entry.path)
    osfunc.is_readable(entry.path, entry.stat)
    if ftstat.S_ISDIR(ft_mode) or ftstat.S_ISAUD(ft_mode):
        osfunc.is_writable(entry.path, entry.stat)
    return filenode.FileNode(entry.path, st_size=st_size, ft_mode=ft_mode)


def build_filetree(path, *, maxdepth=None):
    """Returns a file tree with root at `path`.

    Args:
        path (str): A pathname.
        maxdepth(:obj:`int`, optional): Number of levels to descend.
    """

    def get_depth(path):
        return len(path.split(os.sep)) - 1

    def get_nth_parent(node, nth):
        while nth >= 0:
            node = node.get_parent()
            nth -= 1
        return node

    if os.path.islink(path):
        return _make_filenode(osfunc.DirInfo.from_path(path))
    tree_iter = osfunc.recursive_scandir(osfunc.absrealpath(path),
                                         maxdepth=maxdepth)
    focus = _make_filenode(next(tree_iter))
    base_depth = get_depth(focus.get_value())
    for child in tree_iter:
        child_node = _make_filenode(child)
        child_depth = get_depth(child.path) - base_depth
        focus_depth = focus.get_depth()
        if child_depth > focus_depth:
            focus.append(child_node)
        elif child_depth <= focus_depth:
            get_nth_parent(focus, focus_depth - child_depth).append(child_node)
        else:
            raise RuntimeError(
                "samething went wrong, focus '{0}', next '{1}'".format(
                    os.fspath(focus), os.fspath(child_node)))
        focus = child_node
    return get_nth_parent(focus, focus.get_depth() - 1)


def recursive_listtree(root, *, maxdepth=None, if_cond=None):
    """Yields nodes from the tree including `root`.

    Iterator travels tree using depth-first left-most approach.
    `if_cond` is a function that accept tree node and returns True if that node
    and its subtree should be yield by iterator.

    Args:
        root (:class:`filenode.FileNode`): The root node of tree or subtree.
        maxdepth(:obj:`int`, optional): Number of levels to descend.
        if_cond(:obj:`callable`, optional): Condition that must be met.
    """
    if if_cond is None or if_cond(root):
        yield root
        if maxdepth is None or maxdepth > 0:
            maxdepth = None if maxdepth is None else maxdepth - 1
            for child in root.get_children():
                yield from recursive_listtree(child, maxdepth=maxdepth,
                                              if_cond=if_cond)


def map_tree(tree, *funcs):
    """Returns iterator that appies `funcs` to every node of `tree`."""
    if isinstance(tree, filenode.FileNode):
        tree = recursive_listtree(tree)
    for node in tree:
        for func in funcs:
            node = func(node)
        yield node


def filter_tree(tree, *funcs):
    """
    Returns iterator from those nodes of `tree` for which `funcs` returns True.
    """
    if isinstance(tree, filenode.FileNode):
        tree = recursive_listtree(tree)
    for node in tree:
        for func in funcs:
            if not func(node):
                break
        else:
            yield node


def natsorted_tree(tree, reverse=False):
    """Recursively sorts child nodes in natural order.

    Args:
        tree (:class:`filenode.FileNode`): The tree to sort.
        reverse (:obj:`bool`, optional): Sorting order.
    """
    natsort_key = natsort.natsort_keygen(key=lambda x: x.get_value())
    tree.sort(key=natsort_key, reverse=reverse)
    return tree


def tracksorted_tree(tree, reverse=False):
    """Recursively sorts child nodes by a track number on a disc.

    Nodes, which are of none audio content, unsupported audio content or
    marked for deletion, are placed at the end of the child list.

    Args:
        tree (:class:`filenode.FileNode`): The tree to sort.
        reverse (:obj:`bool`, optional): Sorting order.
    """

    def tracksort_key(node):
        try:
            tags = node.tags
            disc = tags.get(tagcontainer.Names.DISCNUM, 0)
            track = tags.get(tagcontainer.Names.TRACKNUM, 0)
            title = tags.get(tagcontainer.Names.TITLE) or node.get_value()
        except AttributeError:
            disc = track = float('inf')
            title = node.get_value()
        return (disc, track) + natsort.natsort_key(title)

    tree.sort(key=tracksorted_tree, reverse=reverse)
    return tree


# vim: ts=4 sw=4 sts=4 et ai
