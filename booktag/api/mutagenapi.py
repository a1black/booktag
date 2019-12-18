"""Facade for `Mutagen` audio tagging library.

This module supports FLAC, MP3, MP4, Ogg Vorbis and WavPack audio files.
Provided interface provides back and forth translation of supported tagging
standards and internal tagging container.

Mutagen library supports wider range of audio files and tagging formats, but
for the purpose of this application we only require APEv2, ID3, iTunes MP4,
Ogg Vorbis.
"""
import re

from mutagen import (File, FileType, MutagenError, flac, mp3, mp4, wavpack,
                     id3, ogg, oggflac)

from booktag import exceptions
from booktag.utils import ftstat


class SkipTagError(Exception):
    """Raised to skip mapping entry."""


def to_int(value, **kwargs):
    """Returns a new value converted to an integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def to_string(data, **kwargs):
    """Returns a new value converted to a string."""
    return '' if data is None else str(data)


def to_list(data, **kwargs):
    """Returns value converted to a list."""
    try:
        return [data] if isinstance(data, str) else list(data)
    except TypeError:
        return [] if data is None else [data]


def zeroindex_get(value, **kwargs):
    """Returns item at index ``0``."""
    try:
        return to_list(value)[0]
    except IndexError:
        raise SkipTagError


def join_list(value, **kwargs):
    """Returns a string of concatenated values in a list."""
    sep = kwargs.get('sep', '')
    newvalue = sep.join(str(x) for x in to_list(value)).strip()
    if not newvalue:
        raise SkipTagError
    return newvalue


def split_values(value, **kwargs):
    """Splits `value` by the occurrence of delimiter strings."""
    pattern = '|'.join(re.escape(x) for x in to_list(kwargs.get('sep')))
    newvalue = []
    for item in to_list(value):
        newvalue.extend(x.strip() for x in re.split(pattern, str(item)))
    newvalue = list(filter(None, newvalue))
    if not newvalue:
        raise SkipTagError
    return newvalue


def id3_read(tag, *, attr='text', encoding=None, **kwargs):
    """Returns value of an ID3 frame."""
    data = getattr(tag, attr, None)
    data_encoding = getattr(tag, 'encoding', None)
    if not data:
        raise SkipTagError
    elif not encoding or data_encoding != id3.Encoding.LATIN1:
        return data
    newdata = []
    for item in data:
        try:
            newdata.append(data.encode('latin1').decode(encoding))
        except (AttributeError, LookupError, UnicodeError):
            newdata.append(item)
    return newdata


def pair_read(from_, to_index0, to_index1, format):
    """Reads tags that stores pair of values."""
    if format == 'mp3':
        maprule = MP3Read(from_, 'data', split_values, sep='/')
    elif format == 'mp4':
        maprule = MapRule(from_, 'data', zeroindex_get, to_list)
    elif format == 'wav':
        maprule = MapRule(from_, 'data', split_values, sep='/')
    else:
        raise ValueError('unknown tagging standard {0!r}'.format(format))

    def run(source, target, **kwargs):
        data = {}
        maprule(source, data, **kwargs)
        data = data.get('data', [])
        if len(data) > 0:
            target[to_index0] = to_int(data[0])
        if len(data) > 1:
            target[to_index1] = to_int(data[1])

    return run


class MapRule:
    """Class for copying value from one tagging container to another.

    Transformation functions are chained together and modify container value
    in an order they supplied.  Transformation function must take single
    positional argument and a varying number of keyword arguments.

    Args:
        from_ (str): Key in a source container.
        to (str): Key in a target container.
        *transform: List of callable objects that appied to the value.
    """

    def __init__(self, from_, to, *transform, **kwargs):
        self.from_ = from_
        self.to = to
        self.kwargs = kwargs
        self.transform = transform

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, source, target, **kwargs):
        """Copies value from the `source` tagging container to the `target`."""
        try:
            kw = {}
            kw.update(self.kwargs, **kwargs)
            value = source[self.from_]
            for transform in self.transform:
                value = transform(value, **kw)
            target[self.to] = value
        except (KeyError, SkipTagError):
            pass


class MP3Read(MapRule):
    """Class add :func:`id3read` to a list of transformation functions."""

    def __init__(self, from_, to, *transform, **kwargs):
        super().__init__(from_, to, id3_read, *transform, **kwargs)


MP3ReadMapping = [MP3Read('TALB', 'album', join_list, sep=' '),
                  MP3Read('TDRC', 'date', zeroindex_get, to_int),
                  MP3Read('GRP1', 'grouping', zeroindex_get),
                  MP3Read('TIT1', 'grouping', zeroindex_get),
                  MP3Read('TIT2', 'title', join_list, sep=' '),
                  MP3Read('TPE1', 'artist', split_values, sep=','),
                  MP3Read('TPE2', 'albumartist', split_values, sep=','),
                  MP3Read('TCOM', 'composer', split_values, sep=','),
                  MP3Read('TCON', 'genre', split_values, sep=(',', '/')),
                  MP3Read('TPUB', 'label', zeroindex_get),
                  pair_read('TRCK', 'tracknumber', 'tracktotal', 'mp3'),
                  pair_read('TPOS', 'discnumber', 'disctotal', 'mp3')]
# Mappings for MPEG-4 Audio tagging container.
MP4ReadMapping = [MapRule('\xa9alb', 'album', join_list, sep=' '),
                  MapRule('\xa9day', 'date', zeroindex_get, to_int),
                  MapRule('\xa9grp', 'grouping', zeroindex_get),
                  MapRule('\xa9nam', 'title', join_list, sep=' '),
                  MapRule('\xa9ART', 'artist', split_values, sep=','),
                  MapRule('aART', 'albumartist', split_values, sep=','),
                  MapRule('\xa9wrt', 'composer', split_values, sep=','),
                  MapRule('\xa9gen', 'genre', split_values, sep=(',', '/')),
                  pair_read('trkn', 'tracknumber', 'tracktotal', 'mp4'),
                  pair_read('disk', 'discnumber', 'disctotal', 'mp4')]
# Label MP4FreeForm('LABEL', 'UTF-8')
# Mappings for Ogg Vorbis tagging container.
OggReadMapping = [MapRule('album', 'album', join_list, sep=' '),
                  MapRule('date', 'date', zeroindex_get, to_int),
                  MapRule('grouping', 'grouping', zeroindex_get),
                  MapRule('title', 'title', join_list, sep=' '),
                  MapRule('artist', 'artist', split_values, sep=','),
                  MapRule('albumartist', 'albumartist', split_values, sep=','),
                  MapRule('composer', 'composer', split_values, sep=','),
                  MapRule('genre', 'genre', split_values, sep=(',', '/')),
                  MapRule('label', 'label', zeroindex_get),
                  MapRule('tracknumber', 'tracknumber', zeroindex_get, to_int),
                  MapRule('tracktotal', 'tracktotal', zeroindex_get, to_int),
                  MapRule('totaltracks', 'tracktotal', zeroindex_get, to_int),
                  MapRule('discnumber', 'discnumber', zeroindex_get, to_int),
                  MapRule('disctotal', 'disctotal', zeroindex_get, to_int),
                  MapRule('totaldisks', 'disctotal', zeroindex_get, to_int)]
# Mappings for APEv2 tagging container.
WavReadMapping = [MapRule('Album', 'album', join_list, sep=' '),
                  MapRule('Year', 'date', zeroindex_get, to_int),
                  MapRule('Grouping', 'grouping', zeroindex_get),
                  MapRule('Title', 'title', join_list, sep=' '),
                  MapRule('Artist', 'artist', split_values, sep=','),
                  MapRule('Album Artist', 'albumartist', split_values, sep=','),
                  MapRule('Composer', 'composer', split_values, sep=','),
                  MapRule('Genre', 'genre', split_values, sep=(',', '/')),
                  MapRule('Label', 'label', zeroindex_get),
                  pair_read('Track', 'tracknumber', 'tracktotal', 'wav'),
                  pair_read('Disc', 'discnumber', 'disctotal', 'wav')]


def _get_mapping(audiofile, isread=True):
    if isinstance(audiofile, mp3.MP3):
        return MP3ReadMapping if isread else []
    elif isinstance(audiofile, mp4.MP4):
        return MP4ReadMapping if isread else []
    elif isinstance(audiofile, ogg.OggFileType):
        return OggReadMapping if isread else []
    elif isinstance(audiofile, wavpack.WavPack):
        return WavReadMapping if isread else []
    else:
        raise exceptions.FileNotSupportedError


def open(path):
    """Returns Mutagen FileType that contains audio stream info and tags."""
    try:
        fileobj = File(path)
        if fileobj is None:
            raise MutagenError
        if getattr(fileobj, 'tags', None) is None:
            fileobj.add_tags()
        return fileobj
    except TypeError:
        raise TypeError('Open() expected os.PathLike object, got '
                        '{0!r}:'.format(type(path).__name__))
    except (AttributeError, MutagenError):
        raise exceptions.FileNotSupportedError


def read_meta(path, **kwargs):
    """Returns a dictionary that contains audio stream properties and tags."""
    audiofile, metadata = open(path), {}
    mapping = _get_mapping(audiofile, True)
    for reader in mapping:
        reader(audiofile.tags, metadata, **kwargs)
    ft_mode = ftstat.S_IFREG | ftstat.S_IFAUD
    if isinstance(audiofile, mp3.MP3):
        ft_mode |= ftstat.S_IFMP3
    elif isinstance(audiofile, mp4.MP4):
        ft_mode |= ftstat.S_IFMP4
    elif isinstance(audiofile, oggflac.OggFLAC):
        ft_mode |= ftstat.S_IFFLC
    elif isinstance(audiofile, ogg.OggFileType):
        ft_mode |= ftstat.S_IFOGG
    elif isinstance(audiofile, wavpack.WavPack):
        ft_mode |= ftstat.S_IFWAV
    info = getattr(audiofile, 'info', object())
    return dict(tags=metadata, ft_mode=ft_mode,
                bitrate=getattr(info, 'bitrate', 0),
                channels=getattr(info, 'channels', 2),
                length=getattr(info, 'length', 0))


# vim: ts=4 sw=4 sts=4 et ai
