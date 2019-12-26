from booktag.services import metafunc
from booktag.services import treefunc
from booktag.utils import functional


def _count_single_type(tree, *filters):
    count = 0
    for _ in treefunc.filter_tree(tree, *filters):
        count += 1
    return count


def count_dirs(tree):
    return _count_single_type(tree, metafunc.is_dir_node)


def count_files(tree):
    return _count_single_type(tree, metafunc.is_file_node)


def audio_statistic(tree):
    total = supported = todelete = 0
    for node in treefunc.filter_tree(tree, metafunc.is_audio_node):
        total += 1
        if metafunc.is_deleted(node):
            todelete += 1
        if metafunc.is_supported(node):
            supported += 1
    return total, supported, todelete


# vim: ts=4 sw=4 sts=4 et ai
