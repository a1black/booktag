import argparse
import importlib
import json

import humanize
import ruamel.yaml as yaml

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


class PartialParse(argparse.Action):

    def __init__(self, *args, **kwargs):
        kwargs['type'] = argparse.FileType('r')
        self.parser_obj = kwargs.pop('parser', None)
        if not self.parser_obj:
            raise ValueError('missing parser reference')
        if kwargs.get('nargs') is not None:
            raise ValueError('nargs not allowed')
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        parse_queue = getattr(namespace, 'parse_queue', None)
        if parse_queue is None:
            parse_queue = []
            setattr(namespace, 'parse_queue', parse_queue)
        parse_queue.append((self.parser_obj, values))


class PathnameType:
    """
    Factory object that can be passed to the type argument of
    :meth:`argparse.ArgumentParser.add_argument`.

    Args:
        allow_symlink (:obj:`bool`, optional): Allow path to be a symbol link.
        maxsize (:obj:`int`, optional): Maximum file size.
        perm (:obj:`str`, optional): File access rights, 'r' read permissions
             and/or 'w' write permissions.
    """

    def __init__(self, *, allow_symlink=False, ftype=None, maxsize=-1,
                 perm='r'):
        self._allow_symlink = allow_symlink
        self._maxsize = maxsize
        self._type = ftype
        try:
            self._perm = ''.join(sorted(perm)).lower() if perm else None
            if self._perm not in ('r', 'w', 'rw'):
                raise ValueError(
                    "{0}() perm can accept 'r'|'w'|'rw', got {1}".format(
                        type(self).__name__, perm))
        except TypeError:
            raise TypeError(
                '{0}() expected perm to be a string, got {1}'.format(
                    type(self).__name__, type(perm).__name__))

    def __call__(self, value):
        path = osutils.DirEntry(osutils.expandpath(value))
        try:
            if not path.exists():
                raise FileNotFoundError
            elif not self._allow_symlink and path.is_symlink():
                raise argparse.ArgumentTypeError(
                    "path is a symbolic link: '{0}'".format(path))
            elif self._type == 'f' and not path.is_file():
                raise argparse.ArgumentTypeError(
                    "not a file: '{0}'".format(path))
            elif self._type == 'd' and not path.is_dir():
                raise argparse.ArgumentTypeError(
                    "not a directory: '{0}'".format(path))
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
        kwargs = dict(allow_symlink=self._allow_symlink, ftype=self._type,
                      maxsize=self._maxsize, perm=self._perm)
        kwarg_str = ', '.join('{0!s}={1!r}'.format(k, v)
                              for k, v in kwargs.items() if v is not None)
        return '{0}({1})'.format(type(self).__name__, kwarg_str)


def imagestream(value):
    try:
        return ImageStream.from_file(value)
    except exceptions.NotAnImageFileError as error:
        raise TypeError('invalid image file')


def positive_int(value):
    try:
        intval = int(value)
        if intval < 0:
            raise ValueError
        return intval
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "invalid int value: '{0}'".format(value))


def read_config_file(fd):
    """
    Args:
        fd (io.TextIOWrapper): Configuration file descriptor.

    Returns:
        dict: Formated content of configuration file.
    """
    ext = osutils.DirEntry(fd.name).extension.lower()
    try:
        if ext == 'json':
            return json.load(fd)
        else:
            return yaml.safe_load(fd)
    except yaml.YAMLError as error:
        raise exceptions.InvalidConfigurationError(
            fd.name, 'Invalid YAML configuration file') from error
    except json.JSONDecodeError as error:
        raise exceptions.InvalidConfigurationError(
            fd.name, 'Invalid JSON configuraton file') from error


def get_argparser():
    """
    Returns:
        argparse.ArgumentParser: Command-line argument parser.
    """
    # Parser for metadata tags
    metadata_parse = argparse.ArgumentParser(add_help=False)
    metadata_grp = metadata_parse.add_argument_group('Metadata Tags')
    metadata_grp.add_argument(
        '--cover', metavar='<PATH>', type=imagestream,
        action=ArgAction, path=f'album_metadata.{TagName.COVER}',
        help='image file that be used as album cover')
    metadata_grp.add_argument(
        '--author', metavar='NAMES',
        action=ArgAction, path=f'album_metadata.{TagName.ARTIST}',
        help='list of book authors separated by a comma')
    metadata_grp.add_argument(
        '--narrator', metavar='NAMES', action=ArgAction,
        path=f'album_metadata.{TagName.ALBUMARTIST}',
        help='list of book narrators separated by a comma')
    metadata_grp.add_argument(
        '--title', action=ArgAction, path=f'album_metadata.{TagName.ALBUM}',
        help='title of the book')
    metadata_grp.add_argument(
        '--series',
        action=ArgAction, path=f'album_metadata.{TagName.GROUPING}',
        help='name of the book series')
    metadata_grp.add_argument(
        '--series-pos', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.ALBUMSORT}',
        help="book's position in the series")
    metadata_grp.add_argument(
        '--year', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DATE}',
        help='release year of the audio book')
    metadata_grp.add_argument(
        '--orig-year', metavar='YEAR', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.ORIGINALDATE}',
        help='release year of the origin book')
    metadata_grp.add_argument(
        '--publisher', metavar='NAME', action=ArgAction,
        path=f'album_metadata.{TagName.LABEL}', help='name of recording label')
    metadata_grp.add_argument(
        '--genre', action=ArgAction, path=f'album_metadata.{TagName.GENRE}',
        help='list of genres separated by a comma')
    metadata_grp.add_argument(
        '--comment', action=ArgAction,
        path=f'album_metadata.{TagName.COMMENT}',
        help="audio book's commentary")
    metadata_grp.add_argument(
        '--tracktotal', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.TRACKTOTAL}',
        help='number of tracks in album')
    metadata_grp.add_argument(
        '--discnum', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DISCNUM}',
        help='disk number in multi-disc album')
    metadata_grp.add_argument(
        '--disktotal', metavar='NUMBER', type=positive_int,
        action=ArgAction, path=f'album_metadata.{TagName.DISCTOTAL}',
        help='number of discs in multi-disc album')
    # Main parser
    parser = argparse.ArgumentParser(
        prog='booktag', formatter_class=argparse.RawTextHelpFormatter,
        description=DESCRIPTION, epilog=EPILOG)
    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s ({0}) {1}'.format(__licence__, __version__))
    parser.add_argument(
        '--debug', action='store_true', help='Log debug messages')
    parser.add_argument(
        '-c', dest='config', metavar='<PATH>', type=argparse.FileType('r'),
        help='Load metadata tags from JSON or YAML file')
    # Add subparsers
    subparsers = parser.add_subparsers(
        title='Command list', dest='command', metavar='<command>')
    # Add argument for *update* command
    update_cmd = subparsers.add_parser(
        'update', formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[metadata_parse], help='Set metadata tags',
        description='Command-line tool for writing '
        'user defined metadata tags to audio files')
    update_cmd.add_argument(
        'path', metavar='<path>', nargs='+',
        type=PathnameType(allow_symlink=False, perm='rw'),
        help='List of files')
    update_cmd.add_argument(
        '-t', dest='tags', metavar='<PATH>', action=PartialParse,
        parser=metadata_parse,
        help='YAML or JSON file containing metadata tag arguments')
    update_cmd.add_argument(
        '--index', nargs='?', const=True, default=False, type=positive_int,
        action=ArgAction, path=f'metadata.tags.index',
        help='Update track order by sorting file in natural order')
    update_cmd.add_argument(
        '--drop-disc', nargs=0, const=True, default=False,
        action=ArgAction, path='metadata.tags.dropdisc',
        help='Unset disc number and total discs metadta tags')
    update_cmd.add_argument(
        '--dump-cover', nargs=0, const=True, default=False,
        action=ArgAction, path=f'cover_near_file',
        help='place cover art next to audio files')
    return parser


def main():
    # Retrieve command line arguments
    argument_parser = get_argparser()
    arguments = argument_parser.parse_args()
    # Set debug mode
    settings.settings['debug'] = getattr(arguments, 'debug', False)
    # Setup logger
    logger = logutils.setup_root_logger(debug=settings.settings['debug'])
    # Execute command
    command = arguments.command
    if not command:
        argument_parser.error('No command specified')
    try:
        # Load configuration file
        config_file = getattr(arguments, 'config', None)
        if config_file:
            settings.settings.update(read_config_file(config_file))
        # Read extra arguments from user provided files and update application
        # settings object
        patch_pool = []
        for subparser, argfile in getattr(arguments, 'parse_queue', []):
            argstr = []
            for key, value in read_config_file(argfile).items():
                argstr.append('{0:.2s}{1}'.format('-' * len(key), key))
                argstr.append(str(value))
            subarguments = subparser.parse_args(argstr)
            patch_pool.append(getattr(subarguments, 'setting_patch', {}))
        patch_pool.append(getattr(arguments, 'setting_patch', {}))
        # Apply modifications to application settings object
        for patch in patch_pool:
            for key, value in patch.items():
                settings.settings[key] = value
        # Execute command
        cmd = importlib.import_module('booktag.commands.{0}'.format(command))
        cmd.main(*arguments.path)
    except ModuleNotFoundError:
        argument_parser.error('Unknown command: {0}'.format(command))
    except exceptions.CliArgumentError as error:
        argument_parser.error("argument {0}{1}: '{2}'".format(
            '-' if len(error.command) == 1 else '--', error.command, error))
    except OSError as error:
        logger.exception(error.strerror)
        argument_parser.error(
            "{0}: '{1}'".format(error.strerror, error.filename))
    except exceptions.InvalidConfigurationError:
        logger.exception('Invalid configuration')
        argument_parser.error(
            "invalid configuration file: '{0}'".format(config_file))
    except exceptions.AppBaseError as error:
        logger.error('Application error')
        argument_parser.error('application error')
    except Exception:
        logger.exception('Unexpected error')
        argument_parser.error('unexpected error')
