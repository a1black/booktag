import os

from booktag import exceptions
from booktag.app import filenode
from booktag.services import osfunc
from booktag.utils import ftstat


def build_filetree(path, *, maxdepth=None):
    """Returns a file tree with root at `path`.

    Args:
        path (str): A pathname.
        maxdepth(:obj:`int`, optional): Number of levels to descend.

    Raises:
        exceptions.IsASymlinkError: If `path` is a symbol link.
    """

    def get_depth(path):
        return len(path.split(os.sep)) - 1

    def get_nth_parent(node, nth):
        while nth >= 0:
            node = node.get_parent()
            nth -= 1
        return node

    def make_node(entry):
        st_size = getattr(entry.stat, 'st_size', 0)
        ft_mode = ftstat.ft_mode(entry.path, entry.stat)
        if ftstat.S_ISDIR(ft_mode) or ftstat.S_ISAUD(ft_mode):
            osfunc.is_writable(entry.path, entry.stat)
        return filenode.FileNode(entry.path, st_size=st_size, ft_mode=ft_mode)

    if os.path.islink(path):
        raise exceptions.IsASymlinkError(path)
    tree_iter = osfunc.recursive_scandir(osfunc.absrealpath(path),
                                         maxdepth=maxdepth)
    focus = make_node(next(tree_iter))
    base_depth = get_depth(focus.get_value())
    for child in tree_iter:
        child_node = make_node(child)
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


# vim: ts=4 sw=4 sts=4 et ai
