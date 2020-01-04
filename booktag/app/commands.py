"""Collection of functions that are used to build application API."""
import copy

from booktag import exceptions
from booktag.services import metafunc
from booktag.services import treefunc
from booktag.utils import functional


def build_tree(config, path):
    """Command reads build file tree with root at `path`."""
    tree = treefunc.build_filetree(path)
    read_audio_kw = config.get('read.audio', {})
    read_image_kw = config.get('read.image', {})
    for node in treefunc.recursive_listtree(tree):
        if metafunc.is_dir_node(node):
            props = metafunc.read_dir_meta(node)
        elif metafunc.is_image_node(node):
            props = metafunc.read_image_meta(node, **read_image_kw)
        elif metafunc.is_audio_node(node):
            props = metafunc.read_audio_meta(node, **read_audio_kw)
        else:
            props = {}
        node.props.update(props)
    return tree


def update_tree(config, tree):
    """Synchronizes in-memory tree with files on a disk."""
    newtree = treefunc.build_filetree(tree, maxdepth=1)
    if metafunc.get_filetype(tree) != metafunc.get_filetype(newtree):
        raise exceptions.OutdatedFileStatError(tree)
    child_nodes = tree.get_children()
    new_child_nodes = newtree.get_children()
    if child_nodes and new_child_nodes:
        for child in functional.difference(child_nodes, new_child_nodes):
            tree.remove(child)
        for child in functional.difference(new_child_nodes, child_nodes):
            tree.append(build_tree(config, child))
        for child in functional.intersection(child_nodes, new_child_nodes):
            update_tree(config, child)
    return tree


def validate_tree(config, tree):
    """Varifies that file tree can be processed by the application."""
    if metafunc.is_symlink_node(tree):
        raise exceptions.IsASymlinkError(tree)
    count_audio = functional.len(
        treefunc.filter_tree(tree, metafunc.is_audio_node))
    count_supported = functional.len(treefunc.filter_tree(
        tree, metafunc.is_audio_node, metafunc.is_supported,
        functional.not_decorator(metafunc.is_deleted)))
    if count_audio == 0:
        raise exceptions.NotAudioContentError('No audio files found')
    elif (count_supported / count_audio) * 100 <= 50:
        raise exceptions.NotAudioContentError(
            'Too much unsupported audio files: {0}/{1}'.format(
                (count_audio - count_supported), count_audio))


def apply_audio_tags(config, tree, tags):
    """Updates files in the `tree` with values from `meta`."""
    node_filter = (metafunc.is_audio_node, metafunc.is_supported,
                   functional.not_decorator(metafunc.is_deleted))
    for node in treefunc.filter_tree(tree, *node_filter):
        try:
            node.props.tags.update(tags)
        except AttributeError:
            node.props.tags = copy.copy(tags)
        node.notify_observers('update_meta')


def save_audio_tags(config, tree):
    """Writes metadata from objects in `tree` to files on the disk."""
    node_filter = (metafunc.is_audio_node, metafunc.is_supported,
                   functional.not_decorator(metafunc.is_deleted))
    write_audio_kw = config.get('write_setting.audio', {})
    for node in treefunc.filter_tree(tree, *node_filter):
        metafunc.write_audio_meta(node, **write_audio_kw)


# vim: ts=4 sw=4 sts=4 et ai
