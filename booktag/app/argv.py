import argparse

from booktag.app import tags


HELP_DESC = """
Utilite for fill in metadata for an audio book.
"""


class TagAction(argparse.Action):
    """Action for storing value of tagging container."""

    def __init__(self, *args, **kwargs):
        self.tag_name = kwargs.pop('tag', None)
        if not self.tag_name:
            raise ValueError('missing tag name')
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        tag_container = getattr(namespace, 'tags', None)
        if tag_container is None:
            tag_container = tags.Tags()
            setattr(namespace, 'tags', tag_container)
        try:
            tag_container[self.tag_name] = values
        except (TypeError, ValueError):
            raise argparse.ArgumentError(self,
                'invalie value: {0!r}'.format(values))


class _AppArgs:
    """Class for handling command-line arguments."""

    def __init__(self, data):
        self._data = data

    def _fill_read_audio(self, opts):
        """Fills settings for reading audio tags."""
        if self._data.encoding:
            opts['read_setting.audio.encoding'] = self._data.encoding

    def _fill_write_audio(self, opts):
        """Fills settings for writing audio tags."""
        args_map = dict(no_comm='no_comm', no_txxx='no_txxx',
                        no_legal='no_legal', no_web='no_wxxx')
        for arg_name, opt_name in args_map.items():
            flag = getattr(self._data, arg_name, False)
            if flag:
                opts['write_setting.audio.{0}'.format(opt_name)] = flag

    def _fill_run(self, opts):
        """Fills application launch settings."""
        opts['run_setting.path'] = self._data.path
        if self._data.no_ui:
            opts['run_setting.no_ui'] = True

    def get_tags(self):
        """Returns user defined tags."""
        return self._data.tags

    def apply_user_settings(self, config):
        """Sets cofiguration parameters from command-line arguments."""
        self._fill_run(config)
        self._fill_read_audio(config)
        self._fill_write_audio(config)
        return config


def parse():
    """Returns command line arguments."""
    parser = argparse.ArgumentParser(description=HELP_DESC)
    parser.add_argument("path")
    # App options
    parser.add_argument(
        "--encoding",
        help="encoding used to decode ID3v2 tag encoded with ISO-8859-1")
    # Meta options
    parser.add_argument("--author", metavar="NAMES",
                        action=TagAction, tag=tags.Names.ARTIST,
                        help="list of book authors separated by a comma")
    parser.add_argument("--narrator", metavar="NAMES",
                        action=TagAction, tag=tags.Names.ALBUMARTIST,
                        help="list of book narrators separated by a comma")
    parser.add_argument("--title", action=TagAction, tag=tags.Names.ALBUM,
                        help="title of the book")
    parser.add_argument("--series", action=TagAction, tag=tags.Names.GROUPING,
                        help="name of the book series")
    parser.add_argument("--series-pos", metavar="NUMBER",
                        action=TagAction, tag=tags.Names.ALBUMSORT,
                        help="book's position in the series")
    parser.add_argument("--year", action=TagAction, tag=tags.Names.DATE,
                        help="release year of the audio book")
    parser.add_argument("--orig-year", metavar="YEAR",
                        action=TagAction, tag=tags.Names.ORIGINALDATE,
                        help="release year of the origin book")
    parser.add_argument("--publisher", metavar="NAME",
                        action=TagAction, tag=tags.Names.LABEL,
                        help="name of recording label")
    parser.add_argument("--genre", action=TagAction, tag=tags.Names.GENRE,
                        help="list of genres separated by a comma")
    parser.add_argument("--comment", action=TagAction, tag=tags.Names.COMMENT,
                        help="audio book's commentary")
    # Clean-up metadata
    parser.add_argument("--no-comm", action="store_true",
                        help="remove free form tags 'COMM' from ID3 container")
    parser.add_argument("--no-txxx", action="store_true",
                        help="remove free form tags 'TXXX' from ID3 container")
    parser.add_argument("--no-legal", action="store_true",
                        help="remove tags containing legal information")
    parser.add_argument("--no-web", action="store_true",
                        help="remove tags containing URLs")
    # Optional
    parser.add_argument(
        "--no-ui", action="store_true",
        help="update tags without starting command-line user interface")

    return _AppArgs(parser.parse_args())


# vim: ts=4 sw=4 sts=4 et ai
