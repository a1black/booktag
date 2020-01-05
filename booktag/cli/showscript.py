import re

import humanize

from booktag import exceptions
from booktag.api import mutagenapi
from booktag.app import commands
from booktag.services import metafunc
from booktag.utils import functional


class App:
    """Basic script for displaying metadata without user interaction."""

    def __init__(self):
        self._config = {}
        self._view = View()

    def get_config(self):
        return self._config

    def set_config(self, config):
        self._config = config

    def get_view(self):
        return self._view

    def run(self):
        path = self.config.get('path')
        node = commands.build_tree(self.config, path, maxdepth=0)
        if not metafunc.is_supported(node) or metafunc.is_deleted(node):
            raise exceptions.HaltError('content type is not supported')
        elif metafunc.is_image_node(node):
            self.view.show_title('INFO')
            self.view.show_info({
                'type': metafunc.get_content_type_name(node).upper(),
                'size': metafunc.get_filesize(node),
                'width': node.width,
                'height': node.height,
                'mode': node.mode
            })
        elif metafunc.is_audio_node(node):
            raw_tags = mutagenapi.open(node)
            self.view.show_title('INFO')
            self.view.show_info({
                'type': metafunc.get_content_type_name(node).upper(),
                'size': metafunc.get_filesize(node),
                'length': humanize.naturaldelta(node.length),
                'bitrate': humanize.naturalsize(node.bitrate) + 'it/s',
                'channels': node.channels
            })
            self.view.show_title('RAW TAGS')
            self.view.show_tags(raw_tags.tags)
            self.view.show_title('PROCESSED TAGS')
            self.view.show_tags(node.tags)
        else:
            raise exceptions.HaltError(
                'nothing to show, choose image or audio file')
        self.stop()

    def stop(self):
        print()

    config = property(get_config, set_config, doc='Application settings.')
    view = property(get_view)


class View:
    """Methods for formating and printing metadata to STDOUT."""

    def show_title(self, msg):
        print('\n=== {0} ==='.format(msg))

    def show_tags(self, tags):
        maxlen = max(len(x) for x in tags.keys())
        maxlen = 2 if maxlen > 12 else maxlen
        for key, value in sorted(tags.items(), key=lambda x: x[0]):
            if re.search('pic', key, re.I) or isinstance(value, bytes):
                value = '`raw bytes`'
            print('{k:{maxlen}}  {v}'.format(
                k=functional.str_shorten(key, maxlen), v=value, maxlen=maxlen))

    def show_info(self, info):
        label_len = max(len(x) for x in info.keys())
        for key, value in info.items():
            print('{k:{len}}  {v}'.format(k=key, v=value, len=label_len))


# vim: ts=4 sw=4 sts=4 et ai
