"""Facade for `Mutagen` audio tagging library.

This module supports FLAC, MP3, MP4, Ogg Vorbis and WavPack audio files.
Provided interface provides back and forth translation of supported tagging
standards and internal tagging container.

Mutagen library supports wider range of audio files and tagging formats, but
for the purpose of this application we only require APEv2, ID3, iTunes MP4,
Ogg Vorbis.

TODO:
    * :class:`MP3Write` add logging if creating frame istance is failed.
    * Remember about TypeError and ValueError raised by :class:`tags.Tags`.
"""
import re

from mutagen import (File, FileType, MutagenError, flac, mp3, mp4, wavpack,
                     id3, ogg, oggflac)

from booktag import exceptions
from booktag.app import tags
from booktag.utils import functional
from booktag.utils import ftstat


DEFAULT_ID3_DATA_ATTR = 'text'


class SkipTagError(Exception):
    """Raised to skip mapping entry."""


def not_none(value, **kwargs):
    """Checks whether `value` is None or empty string."""
    try:
        if value is None or len(value) == 0:
            raise SkipTagError
    except TypeError:
        pass
    return value


def not_zero(value, **kwargs):
    if value == 0:
        raise SkipTagError
    return value


def to_int(value, **kwargs):
    """Returns a new value converted to an integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def to_string(value, **kwargs):
    """Returns a new value converted to a string."""
    return '' if value is None else str(value)


def to_list(value, **kwargs):
    """Returns value converted to a list."""
    try:
        return [value] if isinstance(value, str) else list(value)
    except TypeError:
        return [] if value is None else [value]


def zeroindex_get(value, **kwargs):
    """Returns item at index ``0``."""
    try:
        return to_list(value)[0]
    except IndexError:
        raise SkipTagError


def join_list(value, **kwargs):
    """Returns a string of concatenated values in a list."""
    sep = kwargs.get('sep', '')
    return sep.join(str(x) for x in to_list(value)).strip()


def split_values(value, **kwargs):
    """Splits `value` by the occurrence of delimiter strings."""
    pattern = '|'.join(re.escape(x) for x in to_list(kwargs.get('sep')))
    newvalue = []
    for item in to_list(value):
        newvalue.extend(x.strip() for x in re.split(pattern, str(item)))
    return list(filter(None, newvalue))


def id3_read(tag, *, attr=DEFAULT_ID3_DATA_ATTR, encoding=None, **kwargs):
    """Returns value of an ID3 frame."""
    data = getattr(tag, attr, None)
    data_encoding = getattr(tag, 'encoding', None)
    if not data:
        raise SkipTagError
    elif encoding and data_encoding == id3.Encoding.LATIN1:
        newdata = []
        for item in data:
            try:
                newdata.append(item.encode('latin1').decode(encoding))
            except (AttributeError, LookupError, UnicodeError):
                newdata.append(item)
        data = newdata
    return data


def pair_read(from_, to_index0, to_index1, format):
    """Reads tags that stores a pair of values."""
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
        if len(data):
            target[to_index0] = to_int(data[0])
        if len(data) > 1:
            target[to_index1] = to_int(data[1])

    return run


def pair_id3_write(from_index0, from_index1, to, format):
    """Writes tags that stores a pair of values."""
    if format == 'mp3':
        maprule = MP3Write('data', to, join_list, sep='/')
    elif format == 'wav':
        maprule = MapWriteRule('data', to, join_list, sep='/')
    else:
        raise ValueError('unknown tagging standard {0!r}'.format(format))

    def run(source, target, **kwargs):
        pair = functional.rstrip([to_int(source.get(from_index0, 0)),
                                  to_int(source.get(from_index1, 0))])
        maprule(dict(data=pair), target, **kwargs)

    return run


def pair_mp4_write(from_index0, from_index1, to):
    """Writes a tuple of track number and total number of tracks."""
    def to_zeroindex_tuple(value, **kwargs):
        newvalue = tuple(value)
        if newvalue == (0, 0):
            raise SkipTagError
        return [newvalue]

    maprule = MapWriteRule('data', to, to_zeroindex_tuple)

    def run(source, target, **kwargs):
        pair = [to_int(source.get(from_index0, 0)),
                to_int(source.get(from_index1, 0))]
        maprule(dict(data=pair), target, **kwargs)

    return run


def drop_tags(if_option, *regexps):
    """Removes tags which match one of the regular expressions."""
    def isuseless(name):
        """Returns True is tag name matches on of the regular expressions."""
        for regexp in regexps:
            if re.match(regexp, name):
                return True
        return False

    def run(source, target, **kwargs):
        """Removes tags from `target` if `if_option` is set in `kwargs`."""
        if if_option is True or kwargs.get(if_option, False):
            external_names = list(target.keys())
            for name in (x for x in external_names if isuseless(x)):
                try:
                    del target[name]
                except KeyError:
                    pass

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
        self.transform = (not_none, *transform, not_none)

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def _process_skipped(self, source, target, **kwargs):
        pass

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
            self._process_skipped(source, target, **kwargs)


class MapWriteRule(MapRule):
    """Class appends :func:`to_list` to the list of translation functions."""

    def __init__(self, from_, to, *transform, **kwargs):
        super().__init__(from_, to, *transform, to_list, **kwargs)

    def _process_skipped(self, source, target, **kwargs):
        """Deletes tag from `target` if that tag not set in `source`."""
        try:
            del target[self.to]
        except KeyError:
            pass


class MP3Read(MapRule):
    """Class adds :func:`id3read` to a list of transformation functions."""

    def __init__(self, from_, to, *transform, **kwargs):
        super().__init__(from_, to, id3_read, *transform, **kwargs)


class MP3Write(MapWriteRule):
    """Class creates ID3 frame object before setting value in a container."""

    def __init__(self, from_, to, *transform, **kwargs):
        super().__init__(from_, to, *transform, **kwargs)
        self.transform += (self.make_frame,)

    def make_frame(self, value, *, attr=DEFAULT_ID3_DATA_ATTR, **kwargs):
        """Returns new instance of ID3 frame."""
        try:
            cls = getattr(id3, self.to)
            return cls(**{attr: value})
        except AttributeError:
            raise SkipTagError
        except (TypeError, ValueError):
            raise SkipTagError


int_val_wrap = (to_int, not_zero, to_string)
# Mapping for reading ID3 tagging container.
MP3ReadMapping = [
    MP3Read('TALB', tags.Names.ALBUM, join_list, sep=' '),
    MP3Read('TDRC', tags.Names.DATE, zeroindex_get, to_int),
    MP3Read('GRP1', tags.Names.GROUPING, zeroindex_get),
    MP3Read('TIT1', tags.Names.GROUPING, zeroindex_get),
    MP3Read('TIT2', tags.Names.TITLE, join_list, sep=' '),
    MP3Read('TPE1', tags.Names.ARTIST, split_values, sep=(',', '&')),
    MP3Read('TPE2', tags.Names.ALBUMARTIST, split_values, sep=(',', '&')),
    MP3Read('TCOM', tags.Names.COMPOSER, split_values, sep=','),
    MP3Read('TCON', tags.Names.GENRE, split_values, sep=(',', '/')),
    MP3Read('TPUB', tags.Names.LABEL, zeroindex_get),
    pair_read('TRCK', tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'mp3'),
    pair_read('TPOS', tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'mp3')
]
# Mappings for MPEG-4 Audio tagging container.
MP4ReadMapping = [
    MapRule('\xa9alb', tags.Names.ALBUM, join_list, sep=' '),
    MapRule('\xa9day', tags.Names.DATE, zeroindex_get, to_int),
    MapRule('\xa9grp', tags.Names.GROUPING, zeroindex_get),
    MapRule('\xa9nam', tags.Names.TITLE, join_list, sep=' '),
    MapRule('\xa9ART', tags.Names.ARTIST, split_values, sep=(',', '&')),
    MapRule('aART', tags.Names.ALBUMARTIST, split_values, sep=(',', '&')),
    MapRule('\xa9wrt', tags.Names.COMPOSER, split_values, sep=(',', '&')),
    MapRule('\xa9gen', tags.Names.GENRE, split_values, sep=(',', '/')),
    pair_read('trkn', tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'mp4'),
    pair_read('disk', tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'mp4')
]
# Label MP4FreeForm('LABEL', 'UTF-8')
# Mappings for Ogg Vorbis tagging container.
OggReadMapping = [
    MapRule('album', tags.Names.ALBUM, join_list, sep=' '),
    MapRule('date', tags.Names.DATE, zeroindex_get, to_int),
    MapRule('grouping', tags.Names.GROUPING, zeroindex_get),
    MapRule('title', tags.Names.TITLE, join_list, sep=' '),
    MapRule('artist', tags.Names.ARTIST, split_values, sep=(',', '&')),
    MapRule('albumartist', tags.Names.ALBUMARTIST, split_values,
            sep=(',', '&')),
    MapRule('composer', tags.Names.COMPOSER, split_values, sep=(',', '&')),
    MapRule('genre', tags.Names.GENRE, split_values, sep=(',', '/')),
    MapRule('label', tags.Names.LABEL, zeroindex_get),
    MapRule('tracknumber', tags.Names.TRACKNUM, zeroindex_get, to_int),
    MapRule('tracktotal', tags.Names.TRACKTOTAL, zeroindex_get, to_int),
    MapRule('totaltracks', tags.Names.TRACKTOTAL, zeroindex_get, to_int),
    MapRule('discnumber', tags.Names.DISCNUM, zeroindex_get, to_int),
    MapRule('disctotal', tags.Names.DISCTOTAL, zeroindex_get, to_int),
    MapRule('totaldisks', tags.Names.DISCTOTAL, zeroindex_get, to_int)
]
# Mappings for APEv2 tagging container.
WavReadMapping = [
    MapRule('Album', tags.Names.ALBUM, join_list, sep=' '),
    MapRule('Year', tags.Names.DATE, zeroindex_get, to_int),
    MapRule('Grouping', tags.Names.GROUPING, zeroindex_get),
    MapRule('Title', tags.Names.TITLE, join_list, sep=' '),
    MapRule('Artist', tags.Names.ARTIST, split_values, sep=(',', '&')),
    MapRule('Album Artist', tags.Names.ALBUMARTIST, split_values,
            sep=(',', '&')),
    MapRule('Composer', tags.Names.COMPOSER, split_values, sep=(',', '&')),
    MapRule('Genre', tags.Names.GENRE, split_values, sep=(',', '/')),
    MapRule('Label', tags.Names.LABEL, zeroindex_get),
    pair_read('Track', tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'wav'),
    pair_read('Disc', tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'wav')
]
# Mapping for writing data into ID3 tagging container.
MP3WriteMapping = [
    drop_tags('no_comm', 'COMM.*'),
    drop_tags('no_txxx', 'TXXX.*'),
    drop_tags('no_wxxx', 'W[A-Z]{3}.*'),
    drop_tags('no_legal', 'TCOP', 'TOWN', 'TPRO'),
    drop_tags(True, 'TMOO', 'PCNT', 'POPM.*'),
    MP3Write(tags.Names.ALBUM, 'TALB', join_list, sep=' '),
    MP3Write(tags.Names.DATE, 'TDRC', *int_val_wrap),
    MP3Write(tags.Names.GROUPING, 'GRP1', join_list, sep=' '),
    MP3Write(tags.Names.GROUPING, 'TIT1', join_list, sep=' '),
    MP3Write(tags.Names.TITLE, 'TIT2', join_list, sep=' '),
    MP3Write(tags.Names.ARTIST, 'TPE1'),
    MP3Write(tags.Names.ALBUMARTIST, 'TPE2'),
    MP3Write(tags.Names.COMPOSER, 'TCOM'),
    MP3Write(tags.Names.GENRE, 'TCON'),
    MP3Write(tags.Names.LABEL, 'TPUB', join_list, sep=' '),
    pair_id3_write(tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'TRCK', 'mp3'),
    pair_id3_write(tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'TPOS', 'mp3')
]
MP4WriteMapping = [
    drop_tags('no_legal', 'cprt', '*.LICENSE'),
    MapWriteRule(tags.Names.ALBUM, '\xa9alb', join_list, sep=' '),
    MapWriteRule(tags.Names.DATE, '\xa9day', *int_val_wrap),
    MapWriteRule(tags.Names.GROUPING, '\xa9grp', join_list, sep=' '),
    MapWriteRule(tags.Names.TITLE, '\xa9nam', join_list, sep=' '),
    MapWriteRule(tags.Names.ARTIST, '\xa9ART'),
    MapWriteRule(tags.Names.ALBUMARTIST, 'aART'),
    MapWriteRule(tags.Names.COMPOSER, '\xa9wrt'),
    MapWriteRule(tags.Names.GENRE, '\xa9gen'),
    pair_mp4_write(tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'trkn'),
    pair_mp4_write(tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'disk')
]
# Mapping for writing data into Ogg Vorbis container.
OggWriteMapping = [
    drop_tags('no_wxxx', 'contact', 'website'),
    drop_tags('no_legal', 'copyright', 'license'),
    drop_tags(True, 'mrat', 'mood', 'rating.*'),
    MapWriteRule(tags.Names.ALBUM, 'album', join_list, sep=' '),
    MapWriteRule(tags.Names.DATE, 'date', *int_val_wrap),
    MapWriteRule(tags.Names.GROUPING, 'grouping', join_list, sep=' '),
    MapWriteRule(tags.Names.TITLE, 'title', join_list, sep=' '),
    MapWriteRule(tags.Names.ARTIST, 'artist'),
    MapWriteRule(tags.Names.ALBUMARTIST, 'albumartist'),
    MapWriteRule(tags.Names.COMPOSER, 'composer'),
    MapWriteRule(tags.Names.GENRE, 'genre'),
    MapWriteRule(tags.Names.LABEL, 'label', join_list, sep=' '),
    MapWriteRule(tags.Names.TRACKNUM, 'tracknumber', *int_val_wrap),
    MapWriteRule(tags.Names.TRACKTOTAL, 'tracktotal', *int_val_wrap),
    MapWriteRule(tags.Names.TRACKTOTAL, 'totaltracks', *int_val_wrap),
    MapWriteRule(tags.Names.DISCNUM, 'discnumber', *int_val_wrap),
    MapWriteRule(tags.Names.DISCTOTAL, 'disctotal', *int_val_wrap),
    MapWriteRule(tags.Names.DISCTOTAL, 'totaldisks', *int_val_wrap),
]
# Mapping for writing data into APEv2 tagging container.
WavWriteMapping = [
    drop_tags('no_wxxx', 'Weblink'),
    drop_tags('no_legal', 'Copyright', 'LICENSE'),
    drop_tags(True, 'Mood'),
    MapWriteRule('Album', tags.Names.ALBUM, join_list, sep=' '),
    MapWriteRule('Year', tags.Names.DATE, *int_val_wrap),
    MapWriteRule('Grouping', tags.Names.GROUPING, join_list, sep=' '),
    MapWriteRule('Title', tags.Names.TITLE, join_list, sep=' '),
    MapWriteRule('Artist', tags.Names.ARTIST),
    MapWriteRule('Album Artist', tags.Names.ALBUMARTIST),
    MapWriteRule('Composer', tags.Names.COMPOSER),
    MapWriteRule('Genre', tags.Names.GENRE),
    MapWriteRule('Label', tags.Names.LABEL, join_list, sep=' '),
    pair_id3_write(tags.Names.TRACKNUM, tags.Names.TRACKTOTAL, 'Track', 'wav'),
    pair_id3_write(tags.Names.DISCNUM, tags.Names.DISCTOTAL, 'Disc', 'wav')
]


def _get_mapping(audiofile, isread=True):
    """Returns a list of rules to move values from one container to another.

    Raises:
        :exc:`exceptions.FileNotSupportedError`: If mapping not defined.
    """
    if isinstance(audiofile, mp3.MP3):
        return MP3ReadMapping if isread else MP3WriteMapping
    elif isinstance(audiofile, mp4.MP4):
        return MP4ReadMapping if isread else MP4WriteMapping
    elif isinstance(audiofile, ogg.OggFileType):
        return OggReadMapping if isread else OggWriteMapping
    elif isinstance(audiofile, wavpack.WavPack):
        return WavReadMapping if isread else WavWriteMapping
    else:
        raise exceptions.FileNotSupportedError


def open(path):
    """Returns Mutagen FileType that contains audio stream info and tags.

    Raises:
        TypeError: Argument of invalid type.
        :exc:`exceptions.FileNotSupportedError`: Unknown file content.
    """
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
    audiofile, metadata = open(path), tags.Tags()
    for reader in _get_mapping(audiofile, isread=True):
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


def write_meta(path, metadata, **kwargs):
    """Writes new metadata into the audio file."""
    audiofile = open(path)
    for writer in _get_mapping(audiofile, isread=False):
        writer(metadata, audiofile.tags, **kwargs)
    audiofile.save()


# vim: ts=4 sw=4 sts=4 et ai
