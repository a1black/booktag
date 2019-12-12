"""Component responsible for building file tree.

:function:`book_path` collects information about files under provided path
and returns internal representation of the file tree.

"""
import errno
import os

from booktag import exceptions
from booktag.utils import ftstat
from booktag.utils import functional
from booktag.utils import tree


def recursive_iterdir(path, *, maxdepth=None):
    """File tree exploration algoritm with start point at the `path`.

    When the `path` points to a file, generator yields single path object.
    When the `path` points to a directory, yield path objects of the directory
    contents.

    This function does not resolve symbolic links. When reading a symbolic
    link function will collect information about the link itself rather then
    the link reference.

    Args:
        path (str): An absolute path to an existing file or directory.
        maxdepth(:obj:`int`, optional): Number of levels to descend.

    Yields:
        str: Path objects of the path contents.

    Raises:
        PermissionError: If service reads path without the adequate access
            rights. Directories and audio files must be accessed for read/write
            operations.
        exceptions.FileNotSupportedError: If path neither file nor directory.
    """
    def access(path, mode):
        """Returns ``True`` if process has read/write permissions."""
        perms = os.R_OK
        if ftstat.S_ISAUD(mode):
            perms |= os.W_OK
        elif ftstat.S_ISDIR(mode):
            perms |= os.W_OK | os.X_OK
        return os.access(path, perms, follow_symlinks=False)

    ft_mode = ftstat.ft_mode(path)
    if not ft_mode:
        raise exceptions.FileNotSupportedError(
            'Neither file nor directory: {}'.format(path))
    elif not access(path, ft_mode):
        raise PermissionError(errno.EACCES, 'Write permission denied', path)
    if maxdepth is None or maxdepth >= 0:
        yield path  # yield current path
        if ftstat.S_ISDIR(ft_mode):  # yield directory contents
            newdepth = None if maxdepth is None else maxdepth - 1
            for filename in os.listdir(path):
                yield from recursive_iterdir(os.path.join(path, filename),
                                             maxdepth=newdepth)


@functional.absnormpath_decr
def path_scan(path):
    """Returns in-memory file tree with root at `path`.

    Args:
        path (str): An absolute path name.

    Raises:
        exceptions.IsASymlinkError: If `path` is a symbol link.
    """
    def path_depth(path):
        sep = os.sep.encode() if isinstance(path, bytes) else os.sep
        return len(path.split(sep)) - 2  # -1-1 for leading os.sep and for len

    def make_node(path, parent):
        stat = os.stat(path, follow_symlinks=False)
        child = tree.Node(path, ft_mode=ftstat.ft_mode(path),
                          st_size=getattr(stat, 'st_size', 0))
        if parent is not None:
            child.set_value(os.path.split(path)[1])
            parent.append(child)
        return child

    def go_up(node, depth):
        """Returns closest ancestor vertex that has depth `depth`."""
        try:
            while node.get_depth() > depth:
                node = node.get_parent()
            return node
        except (AttributeError, TypeError):
            raise RuntimeError('impossible to reach depth {0}'.format(depth))

    focus_node = None
    base_depth = path_depth(path)
    for cur_path in recursive_iterdir(path, maxdepth=None):
        cur_depth = path_depth(cur_path) - base_depth
        focus_depth = None if focus_node is None else focus_node.get_depth()
        if cur_depth == 0 and focus_depth is None:  # root vertex
            focus_node = make_node(cur_path, None)
        elif cur_depth == focus_depth:  # sibling vertex
            focus_node = make_node(cur_path, focus_node.get_parent())
        elif cur_depth > focus_depth:  # child vertex, depth growth is +1
            focus_node = make_node(cur_path, focus_node)
        elif cur_depth < focus_depth:  # ancestor vertex
            focus_node = make_node(cur_path, go_up(focus_node, cur_depth - 1))
        else:
            raise RuntimeError('samething went wrong placing node {0!r} in '
                               '{1!r}'.format(cur_path, path))
    root = go_up(focus_node, 0)
    if ftstat.S_ISLNK(root.props.ft_mode):
        raise exceptions.IsASymlinkError(path)
    return root


# vim: ts=4 sw=4 sts=4 et ai
