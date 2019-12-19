import argparse

from booktag.app import tags


HELP_DESC = """
Utilite for fill in metadata for an audio book.
"""


def _fetch_args(args, mapping):
    """Returns command line arguments specified by `mapping`."""
    values = {}
    for arg, tag in mapping.items():
        value = args.get(arg, None)
        if value:
            values[tag] = value
    return values


def fetch_args_meta_values(args):
    """Returns audio tags provided through the command line."""
    args_map = dict(author=tags.Names.ARTIST, narrator=tags.Names.ALBUMARTIST,
                    title=tags.Names.ALBUM, series=tags.Names.GROUPING,
                    year=tags.Names.DATE, orig_year=tags.Names.ORIGINALDATE,
                    series_pos=tags.Names.ALBUMSORT, genre=tags.Names.GENRE,
                    publisher=tags.Names.LABEL, comment=tags.Names.COMMENT)
    return _fetch_args(args, args_map)


def fetch_args_meta_config(args):
    """Returns settings for reading/writing audio tags."""
    args_map = dict(encoding='encoding', no_comm='no_comm', no_txxx='no_txxx',
                    no_legal='no_legal', no_web='no_wxxx')
    return _fetch_args(args, args_map)


def fetch_args_app_config(args):
    """Returns application settings."""
    args_map = dict(path='path', no_cli='no_cli')
    return _fetch_args(args, args_map)


def get_args():
    """Returns command line arguments."""
    parser = argparse.ArgumentParser(description=HELP_DESC)
    parser.add_argument("path")
    # App options
    parser.add_argument(
        "--encoding",
        help="encoding used to decode ID3v2 tag encoded with ISO-8859-1")
    # Meta options
    parser.add_argument("--author", metavar="NAMES",
                        help="list of book authors separated by a comma")
    parser.add_argument("--narrator", metavar="NAMES",
                        help="list of book narrators separated by a comma")
    parser.add_argument("--title", help="title of the book")
    parser.add_argument("--series", help="name of the book series")
    parser.add_argument("--series-pos", type=int, metavar="NUMBER",
                        help="book's position in the series")
    parser.add_argument("--year", type=int,
                        help="release year of the audio book")
    parser.add_argument("--orig-year", type=int, metavar="YEAR",
                        help="release year of the origin book")
    parser.add_argument("--publisher", metavar="NAME",
                        help="name of recording label")
    parser.add_argument("--genre", help="list of genres separated by a comma")
    parser.add_argument("--comment", help="audio book's commentary")
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
        "--no-cli", action="store_true",
        help="update tags without starting command-line user interface")

    return parser.parse_args()
