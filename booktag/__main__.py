import argparse
import importlib

import humanize

from booktag import exceptions
from booktag import logutils
from booktag import osutils
from booktag import settings
from booktag.constants import TagName
from booktag.streams import ImageStream


__licence__ = 'MIT'
__version__ = '0.0.1'

DESCRIPTION = '''
Command-line tools for working with audio files.

Application is designed to work with collection of audio files containing
single media album, specifically an audio book.
'''
EPILOG = ''


class ArgAction(argparse.Action):
    """Stores `(key, value)` pair in a patch for application settings."""

    def __init__(self, *args, **kwargs):
        self.setting_key = kwargs.pop('path', None)
        if not self.setting_key:
            raise ValueError('missing key in setting object')
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        patch = getattr(namespace, 'setting_patch', None)
        if patch is None:
            patch = {}
            setattr(namespace, 'setting_patch', patch)
        patch[self.setting_key] = values


class ArgFlagAction(ArgAction):
    """Stores `(key, True)` pair in a path for application settings."""

    def __init__(self, *args, **kwargs):
        kwargs['const'] = True
        kwargs['default'] = False
        kwargs['nargs'] = 0
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        super().__call__(parser, namespace, True, option_string)


class PathnameType:
    """
    Factory object that can be passed to the type argument of
    :meth:`argparse.ArgumentParser.add_argument`.

    Args:
        allow_symlink (:obj:`bool`, optional): Allow path to be a symbol link.
        exists (:obj:`bool`, optional): Pathname must exist.
        maxsize (:obj:`int`, optional): Maximum file size (only for files).
        perm (:obj:`str`, optional): File access rights, 'r' read permissions
             and/or 'w' write permissions (only if `exists` is True).
    """

    def __init__(self, *, allow_symlink=False, exists=True, maxsize=-1,
                 perm='r'):
        self._allow_symlink = allow_symlink if exists else True
        self._exists = exists
        self._maxsize = maxsize if exists else -1
        try:
            self._perm = ''.join(sorted(perm)).lower() if perm else None
            if self._perm not in ('r', 'w', 'rw'):
                raise ValueError(
                    "{0}() perm can accept 'r'|'w'|'rw', got {1}".format(
                        type(self).__name__, perm))
            elif not exists:
                self._perm = None
        except TypeError:
            raise TypeError(
                '{0}() expected perm to be a string, got {1}'.format(
                    type(self).__name__, type(perm).__name__))

    def __call__(self, value):
        path = osutils.DirEntry(osutils.expandpath(value))
        try:
            if self._exists and not path.exists():
                raise FileNotFoundError
            elif not self._allow_symlink and path.is_symlink():
                raise argparse.ArgumentTypeError(
                    "path is a symbolic link: '{0}'".format(path))
            elif path.is_file() and 0 <= self._maxsize < path.size():
                raise argparse.ArgumentTypeError(
                    "file size {0} exceeds limit {1}: '{2}'".format(
                        humanize.naturalsize(path.size(), gnu=True),
                        humanize.naturalsize(self._maxsize, gnu=True), path))
            elif self._perm:
                osutils.chmod(
                    path, read='r' in self._perm, write='w' in self._perm)
            return path
        except FileNotFoundError:
            raise argparse.ArgumentTypeError(
                "no such file or directory: '{0}'".format(path))
        except PermissionError:
            mode = '/'.join(v for k, v in dict(r='read', w='write').items()
                            if k in self._perm)
            raise argparse.ArgumentTypeError(
                "no {0} access permissions: '{0}'".format(mode, path))

    def __repr__(self):
        kwargs = dict(allow_symlink=self._allow_symlink, exists=self._exists,
                      maxsize=self._maxsize, perm=self._perm)
        kwarg_str = ', '.join('{0!s}={1!r}'.format(k, v)
                              for k, v in kwargs.items() if v is not None)
        return '{0}({1})'.format(type(self).__name__, kwarg_str)


class ImageFileType(PathnameType):
    """
    Factory object that can be passed to the type argument of
    :meth:`argparse.ArgumentParser.add_argument`.
    """

    def __init__(self, maxsize=5242880):
        super().__init__(allow_symlink=True, exists=True, maxsize=maxsize,
                         perm='r')

    def __call__(self, value):
        path = super().__call__(value)
        try:
            return ImageStream.from_file(path)
        except exceptions.NotAnImageFileError:
            raise argparse.ArgumentTypeError(
                'invalid image file: {0}'.format(path))

    def __repr__(self):
        return '{0}(maxsize={1!r})'.format(type(self).__name__, self._maxsize)


def positive_int(value):
    try:
        intval = int(value)
        if intval < 0:
            raise ValueError
        return intval
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "invalid int value: '{0}'".format(value))


def get_argparser():
    """
    Returns:
        argparse.ArgumentParser: Command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        prog='booktag', formatter_class=argparse.RawTextHelpFormatter,
        description=DESCRIPTION, epilog=EPILOG)
    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s ({0}) {1}'.format(__licence__, __version__))
    parser.add_argument('--debug', action='store_true')
    # Add subparsers
    subparsers = parser.add_subparsers(
        title='Command list', dest='command', metavar='<command>')
    # Add argument for *update* command
    update_cmd = subparsers.add_parser(
        'update', formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Set metadata tags', description='Command-line tool for writing '
        'user defined metadata tags to audio files.')
    update_cmd.add_argument(
        'path', metavar='<path>', nargs='+',
        type=PathnameType(allow_symlink=False, perm='rw'),
        help='List of files')
    update_cmd.add_argument(
        '-c', dest='config', metavar='<PATH>',
        type=PathnameType(allow_symlink=True, maxsize=2048, perm='r'),
        help='Load metadata tags from JSON or YAML file')
    update_cmd.add_argument(
        '--dump-cover', action=ArgFlagAction, path=f'cover_near_file',
        help='place cover art next to audio files')
    update_cmd.add_argument(
        '--keep-tracknum',
        action=ArgFlagAction, path=f'metadata.tags.keeptracknum',
        help='Do not update tracknum and tracktotal metadata tags')
    update_cmd.add_argument(
        '--keep-discnum',
        action=ArgFlagAction, path=f'metadata.tags.keepdiscnum',
        help='Do not update discnum and disctotal metadata tags')
    update_grp = update_cmd.add_argument_group('Metadata Tags')
    update_grp.add_argument(
        '--cover', metavar='<PATH>', type=ImageFileType(),
        action=ArgAction, path=f'album_metadata.{TagName.COVER}',
        help='image file that be used as album cover')
    update_grp.add_argument(
        '--author', metavar='NAMES',
        action=ArgAction, path=f'album_metadata.{TagName.ALBUM}',
        help='list of book authors separated by a comma')
    update_grp.add_argument(
        '--narrator', metavar='NAMES', action=ArgAction,
        path=f'album_metadata.{TagName.ALBUMARTIST}',
        help='list of book narrators separated by a comma')
    update_grp.add_argument(
        '--title', action=ArgAction, path=f'album_metadata.{TagName.ALBUM}',
        help='title of the book')
    update_grp.add_argument(
        '--series',
        action=ArgAction, path=f'album_metadata.{TagName.GROUPING}',
        help='name of the book series')
    update_grp.add_argument(
        '--series-pos', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.ALBUMSORT}',
        help="book's position in the series")
    update_grp.add_argument(
        '--year', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DATE}',
        help='release year of the audio book')
    update_grp.add_argument(
        '--orig-year', metavar='YEAR', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.ORIGINALDATE}',
        help='release year of the origin book')
    update_grp.add_argument(
        '--publisher', metavar='NAME', action=ArgAction,
        path=f'album_metadata.{TagName.LABEL}', help='name of recording label')
    update_grp.add_argument(
        '--genre', action=ArgAction, path=f'album_metadata.{TagName.GENRE}',
        help='list of genres separated by a comma')
    update_grp.add_argument(
        '--comment', action=ArgAction,
        path=f'album_metadata.{TagName.COMMENT}',
        help="audio book's commentary")
    update_grp.add_argument(
        '--tracknum', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.TRACKNUM}',
        help='starting index for track numbering')
    update_grp.add_argument(
        '--tracktotal', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.TRACKTOTAL}',
        help='number tracks in an album')
    update_grp.add_argument(
        '--discnum', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DISCNUM}',
        help='disk number in multi-disc album')
    update_grp.add_argument(
        '--disktotal', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DISCTOTAL}',
        help='number of discs in multi-disc album'
    )
    return parser


def main():
    # Retrieve command line arguments
    argument_parser = get_argparser()
    arguments = argument_parser.parse_args()
    # Setup logger
    settings.settings['debug'] = getattr(arguments, 'debug', False)
    logger = logutils.setup_root_logger(settings.settings['debug'])
    command = arguments.command
    if not command:
        argument_parser.error('No command specified')
    config = getattr(arguments, 'config', None)
    try:
        # Apply command-line arguments to setting object
        if config:
            settings.settings.from_file(config)
        for key, value in getattr(arguments, 'setting_patch', {}).items():
            settings.settings[key] = value
        # Execute command
        cmd = importlib.import_module('booktag.commands.{0}'.format(command))
        cmd.main(*arguments.path)
    except ModuleNotFoundError:
        argument_parser.error('Unknown command: {0}'.format(command))
    except OSError as error:
        logger.exception(error.strerror)
        argument_parser.error(
            "{0}: '{1}'".format(error.strerror, error.filename))
    except exceptions.CliArgumentError as error:
        argument_parser.error("argument {0}{1}: '{2}'".format(
            '-' if len(error.command) == 1 else '--', error.command, error))
    except settings.InvalidConfigurationError:
        logger.exception('Configuration error')
        argument_parser.error(
            "invalid configuration file: '{0}'".format(config))
    except exceptions.AppBaseError as error:
        logger.error('Application error')
        argument_parser.error('application error')
    except Exception:
        logger.exception('Unexpected error')
        argument_parser.error('unexpected error')
