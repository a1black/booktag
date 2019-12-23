import copy

from booktag import exceptions
from booktag.services import metafunc
from booktag.services import treefunc


class BuildTree:
    def run(self, config, path):
        tree = treefunc.build_filetree(path)
        if (not tree.has_children() and metafunc.is_dir_node(tree)):
            raise exceptions.DirectoryIsEmpty(tree)
        read_audio_kw = config.get('metareding.audio', {})
        read_image_kw = config.get('metareding.image', {})
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


class SetAudioMeta:
    def run(self, config, tree, meta):
        node_filter = (metafunc.is_audio_node, metafunc.is_supported,
                       metafunc.not_decorator(metafunc.is_deleted))
        for node in treefunc.filter_tree(tree, *node_filter):
            try:
                node.props.tags.update(meta)
            except AttributeError:
                node.props.tags = copy.copy(meta)
            node.notify_observers('update_meta')


class SaveAudioMeta:
    def run(self, config, tree, meta):
        node_filter = (metafunc.is_audio_node, metafunc.is_supported,
                       metafunc.not_decorator(metafunc.is_deleted))
        write_audio_kw = config.get('metasaving.audio', {})
        for node in treefunc.filter_tree(tree, *node_filter):
            metafunc.write_audio_meta(node, **write_audio_kw)
