from booktag.services import metafunc
from booktag.services import treefunc
from booktag.utils import functional


def _count_single_type(tree, *filters):
    count = 0
    for _ in treefunc.filter_tree(tree, *filters):
        count += 1
    return count


def _filetype_statistic(tree, *filters):
    """
    Returns a tuple that contains number of supported, unsupported and
    marked for deletion files.
    """
    supported = unsupported = deleted = 0
    for node in treefunc.filter_tree(tree, *filters):
        if metafunc.is_deleted(node):
            deleted += 1
        elif metafunc.is_supported(node):
            supported += 1
        else:
            unsupported += 1
    return supported, unsupported, deleted


def count_dirs(tree):
    return _count_single_type(tree, metafunc.is_dir_node)


def count_files(tree):
    return _count_single_type(tree, metafunc.is_file_node)


def audio_statistic(tree):
    """Returns a tuple `(suppported count, unsupported count, deleted)`."""
    return _filetype_statistic(tree, metafunc.is_audio_node)


def image_statistic(tree):
    """Returns a tuple `(suppported count, unsupported count, deleted)`."""
    return _filetype_statistic(tree, metafunc.is_image_node)


def total_statistic(tree):
    total = files = dirs = symlinks = 0
    for node in treefunc.recursive_listtree(tree):
        total += 1
        if metafunc.is_file_node(node):
            files += 1
        elif metafunc.is_dir_node(node):
            dirs += 1
        elif metafunc.is_symlink_node(node):
            symlinks += 1
    return total, dirs, files, symlinks


# vim: ts=4 sw=4 sts=4 et ai
