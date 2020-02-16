"""Facade for `Mutagen` audio tagging library.

Mutagen library supports wider range of audio files and tagging formats, but
for the purpose of this application we only require ID3, MPEG4, Ogg Vorbis.

TODO:
    * :class:`MP3Write` add logging if creating frame istance is failed.
    * Remember about TypeError and ValueError raised by tag container.
"""
import abc
import base64
import logging
import os
import re

from mutagen import (File, MutagenError, mp3, mp4, id3, ogg, flac)

from booktag import exceptions
from booktag import streams
from booktag.constants import AudioType, ImageType, PictureType, TagName


logger = logging.getLogger(__name__)


class SkipTagError(Exception):
    """Raised to skip mapping entry."""


class Mapping:

    def __init__(self, *rules, **useless):
        self._rules = []
        self._useless = {}
        for rule in rules:
            self.add_rule(rule)
        for key, value in useless.items():
            self.add_useless(key, *value)

    def __iter__(self):
        return iter(self._rules)

    def add_rule(self, rule):
        self._rules.append(rule)

    def add_useless(self, namespace, *exps):
        self._useless[namespace] = exps

    def get_useless(self, namespace):
        return self._useless.get(namespace, [])


class AbstractMapRule(metaclass=abc.ABCMeta):
    """Abstract rule to copy value from one dictionary to another.

    Args:
        *filters: List of callable objects that modifies copied value.
    """

    def __init__(self, *filters):
        self._filters = []
        for filter_obj in filters:
            self.add_filter(filter_obj)

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    @abc.abstractmethod
    def _execute(self, source, target):
        raise NotImplementedError

    def _filter(self, value):
        for filter_obj in self._filters:
            value = filter_obj(value)
            if value is None:
                raise SkipTagError
        return value

    def add_filter(self, function):
        if isinstance(function, type) and issubclass(function, AbstractFilter):
            function = function()
        self._filters.append(function)

    def get_tag(self, source, key):
        value = source.get(key, None)
        if value is None:
            raise SkipTagError
        return value

    def set_tag(self, target, key, value):
        try:
            if value is None:
                del target[key]
            elif hasattr(target, 'add') and callable(target.add):
                target.add(value)
            else:
                target[key] = value
        except KeyError:
            pass
        except (TypeError, ValueError) as error:
            logger.exception(
                '{0}[{1}] got invalid tag value {2!s}: {3}'.format(
                    type(target).__name__, key, type(value).__name__, value))
            raise SkipTagError

    def run(self, source, target):
        try:
            return self._execute(source, target)
        except SkipTagError:
            self.set_tag(target, self._to, None)


class AbstractFilter(metaclass=abc.ABCMeta):
    """Abstract object called on copied tag value."""

    def __init__(self, **kwargs):
        self._options = kwargs

    def __call__(self, value):
        return self.run(value)

    @abc.abstractmethod
    def run(self, value):
        raise NotImplementedError


class AbstractPictureRule(AbstractMapRule, metaclass=abc.ABCMeta):
    """Abstract class for handling embedded picture tags."""

    PRIORITY_ORDER = (PictureType.COVER_FRONT, PictureType.COVER_BACK,
                      PictureType.OTHER, PictureType.LEAFLET_PAGE,
                      PictureType.MEDIA, PictureType.LEAD_ARTIST,
                      PictureType.ARTIST, PictureType.ILLUSTRATION)

    def __init__(self, source_key, *filters):
        super().__init__(*filters)
        self._from = source_key
        self._to = TagName.COVER

    def get_tag(self, source, key, silent=False):
        if hasattr(source, 'getall'):
            value = source.getall(key)
        else:
            value = source.get(key, None) or []
        if not value and not silent:
            raise SkipTagError
        return value


class MoveTag(AbstractMapRule):
    """
    Args:
        source_key (str): Key in the source dictionary to retrieve tag value.
        target_key (str): Key in the target dictionary to store tag value.
        *filters: List of callable which applied to tag value before setting
            it to the target dictionary.
    """

    def __init__(self, source_key, target_key, *filters):
        super().__init__(*filters)
        self._from = source_key
        self._to = target_key

    def _execute(self, source, target):
        value = self._filter(self.get_tag(source, self._from))
        self.set_tag(target, self._to, value)


class ID3In(AbstractFilter):
    """Filter for wrapping value into Mutagen ID3 frame structure."""

    def run(self, value):
        try:
            data_attr = self._options.get('attr', 'text')
            cls = self._options['cls']
            if not isinstance(value, dict):
                value = {data_attr: value}
            return cls(**value)
        except KeyError:
            raise ValueError('ID3In() missing type of ID3 frame')


class ID3Out(AbstractFilter):
    """Filter for retrieving value from Mutagen implementation of ID3 frame."""

    def run(self, value):
        data_attr = self._options.get('attr', 'text')
        return getattr(value, data_attr, None)


class FirstItem(AbstractFilter):
    """Filter retrieves first item in a list, otherwise returns value."""

    def run(self, value):
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        else:
            return value


class ToInt(AbstractFilter):
    """Filter converts value to an integer."""

    def run(self, value):
        try:
            value = int(value)
            if self._options.get('notzero') and value == 0:
                value = None
            if self._options.get('positive') and value < 0:
                value = None
        except (TypeError, ValueError):
            value = None
        return value


class ToStr(AbstractFilter):
    """
    Filter converts value to a string or joins iterables using `sep` character.
    """

    def run(self, value):
        if isinstance(value, (list, tuple)):
            sep = self._options.get('sep', ' ')
            value = sep.join(str(x) for x in value)
        value = str(value).strip()
        if self._options.get('notempty', True) and not value:
            value = None
        return value


class ToList(AbstractFilter):
    """Filter wrappes value into a list."""

    def run(self, value):
        try:
            value = [value] if isinstance(value, (str, bytes)) else list(value)
        except TypeError:
            value = [value]
        value = list(filter(lambda x: x is not None and x != '', value))
        if self._options.get('notempty', True) and not value:
            value = None
        return value


class ToListFirstTuple(ToList):

    def run(self, value):
        value = super().run(value)
        if value is not None:
            value = [tuple(value)]
        return value


class SplitStr(AbstractFilter):
    """Filter split string into a list of values using `sep` string."""

    def run(self, value):
        sep = self._options.get('sep')
        if not (sep or isinstance(sep, (list, tuple))):
            raise ValueError("SplitStr() missing separator string")
        pattern = '|'.join(re.escape(x) for x in sep)
        newvalue = []
        for item in ToList(notempty=False).run(value):
            newvalue.extend(x.strip() for x in re.split(pattern, str(item)))
        value = list(filter(None, newvalue))
        if self._options.get('notempty', True) and not value:
            value = None
        return value


class Year(AbstractFilter):
    """Filter retrieves year part of a timestamp."""

    def run(self, value):
        try:
            value = int(getattr(value, 'year', 0))
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else None


class VorbisCover(AbstractFilter):
    """Filter transforms encoded string into a image object."""

    def run(self, value):
        try:
            return flac.Picture(base64.b64decode(value))
        except (TypeError, ValueError):
            return None


class Mp4Cover(AbstractFilter):
    """Filters wraps tag into a dictionary."""

    def run(self, value):
        if isinstance(value, bytes) and len(value):
            return dict(data=value, type=PictureType.COVER_FRONT)
        else:
            return None


class ToApic(AbstractFilter):
    """Filter converts raw image data to ID3 frame."""

    def run(self, value):
        try:
            if isinstance(value, bytes):
                value = streams.ImageStream.from_file(value)
            return id3.APIC(data=value.data, type=PictureType.COVER_FRONT,
                            desc='', mime=value.mime)
        except AttributeError:
            raise SkipTagError


class ToMp4Cover(AbstractFilter):
    """Filter prepares raw image data."""

    def run(self, value):
        """
        Args:
            value (streams.ImageStream): Raw image data.

        Returns:
            mp4.MP4Cover: MP4 metadata tag.
        """
        try:
            if isinstance(value, bytes):
                value = streams.ImageStream.from_file(value)
            if value.format == ImageType.PNG:
                imgformat = mp4.MP4Cover.FORMAT_PNG
            else:
                imgformat = mp4.MP4Cover.FORMAT_JPEG
            return mp4.MP4Cover(value.data, imgformat)
        except AttributeError:
            raise SkipTagError


class ToVorbisCover(AbstractFilter):
    """Filter converts raw image data to base64 encoded string."""

    def run(self, value):
        """
        Args:
            value (streams.ImageStream): Raw image data

        Returns:
            str: Vorbis metadata tag.
        """
        try:
            if isinstance(value, bytes):
                value = streams.ImageStream.from_file(value)
            picture = flac.Picture()
            picture.data = value.data
            picture.mime = value.mime
            picture.type = PictureType.COVER_FRONT
            picture.height = value.height
            picture.width = value.width
            picture.desc = ''
            encoded = base64.b64encode(picture.write())
            return encoded.decode('ascii')
        except AttributeError:
            raise SkipTagError


class PairTag(MoveTag):
    """Rule to read value from metadata tag, like 'track/total'."""

    def __init__(self, source_key, target_key0, target_key1, *filters):
        super().__init__(source_key, (target_key0, target_key1), *filters)

    def _execute(self, source, target):
        value = self._filter(self.get_tag(source, self._from)) + [None] * 2
        for target_key, index_value in zip(self._to, value):
            try:
                index_value = ToInt(notzero=False).run(index_value)
                self.set_tag(target, target_key, index_value)
            except SkipTagError:
                pass


class ToPairTag(MoveTag):
    """Rule to write pair of values to metadata tag, like 'track/total'."""

    def __init__(self, source_key0, source_key1, target_key, *filters):
        super().__init__((source_key0, source_key1), target_key, *filters)

    def run(self, source, target):
        value = []
        for index, source_key in enumerate(self._from):
            index_value = ToInt(notzero=True, positive=True).run(
                self.get_tag(source, source_key))
            if index == 0 and index_value is None:
                raise SkipTagError
            value.append(index_value or 0)
        self.set_tag(target, self._to, self._filter(value))


class PictureIn(AbstractPictureRule):
    """Class creates metadata tag from raw image data."""

    def _execute(self, source, target):
        from_key, to_key = self._to, self._from
        # Get album cover
        cover = self.get_tag(source, from_key, silent=True)
        if cover:
            embedded = self.get_tag(target, to_key, silent=True)
            for pic in (x for x in embedded if hasattr(x, 'desc')):
                self.set_tag(target, '{0}:{1}'.format(to_key, pic.desc), None)
            self.set_tag(target, to_key, self._filter(cover))


class PictureOut(AbstractPictureRule):
    """Class retrieves raw image data from metadata tag."""

    def _embedded_iter(self, tagcontainer):
        """
        Args:
            tagcontainer (dict): Metadata tags.

        Yields:
            streams.ImageStream: Embedded pictures.
        """
        weights = {tp: pr
                   for tp, pr in zip(self.PRIORITY_ORDER, range(100, 0, -10))}
        pictures = []
        for pic in self.get_tag(tagcontainer, self._from, True):
            try:
                pic = self._filter(pic)
                if not hasattr(pic, 'type'):
                    pic.type = PictureType.COVER_FRONT
                pictures.append(pic)
            except SkipTagError:
                continue
        pictures.sort(key=lambda x: weights.get(x.type, 0), reverse=True)
        for pic in pictures:
            yield pic

    def _execute(self, source, target):
        for picture in self._embedded_iter(source):
            try:
                self.set_tag(target, self._to,
                             streams.ImageStream.from_file(picture.data))
                break
            except (AttributeError, exceptions.NotAnImageFileError):
                continue


# Mapping for reading ID3 tagging container.
MP3ReadMapping = [
    PictureOut('APIC'),
    MoveTag('TALB', TagName.ALBUM, ID3Out, ToStr),
    MoveTag('TDRC', TagName.DATE, ID3Out, Year),
    MoveTag('GRP1', TagName.GROUPING, ID3Out, ToStr),
    MoveTag('TIT1', TagName.GROUPING, ID3Out, ToStr),
    MoveTag('TIT2', TagName.TITLE, ID3Out, ToStr),
    MoveTag('TPE1', TagName.ARTIST, ID3Out, SplitStr(sep=[',', '&', '/'])),
    MoveTag('TPE2', TagName.ALBUMARTIST, ID3Out,
            SplitStr(sep=[',', '&', '/'])),
    MoveTag('TCOM', TagName.COMPOSER, ID3Out, SplitStr(sep=[',', '&', '/'])),
    MoveTag('TCON', TagName.GENRE, ID3Out, SplitStr(sep=[',', '/'])),
    MoveTag('TPUB', TagName.LABEL, ID3Out, ToStr),
    PairTag('TRCK', TagName.TRACKNUM, TagName.TRACKTOTAL, ID3Out, FirstItem,
            SplitStr(sep=['/'], notempty=True)),
    PairTag('TPOS', TagName.DISCNUM, TagName.DISCTOTAL, ID3Out, FirstItem,
            SplitStr(sep=['/'], notempty=True))
]
# Mappings for MPEG-4 Audio tagging container.
MP4ReadMapping = [
    PictureOut('covr', Mp4Cover),
    MoveTag('\xa9alb', TagName.ALBUM, ToStr),
    MoveTag('\xa9day', TagName.DATE, FirstItem, ToInt(notzero=True)),
    MoveTag('\xa9grp', TagName.GROUPING, ToStr),
    MoveTag('\xa9nam', TagName.TITLE, ToStr),
    MoveTag('\xa9ART', TagName.ARTIST, SplitStr(sep=[',', '&', '/'])),
    MoveTag('aART', TagName.ALBUMARTIST, SplitStr(sep=[',', '&', '/'])),
    MoveTag('\xa9wrt', TagName.COMPOSER, SplitStr(sep=[',', '&', '/'])),
    MoveTag('\xa9gen', TagName.GENRE, SplitStr(sep=[',', '/'])),
    PairTag('trkn', TagName.TRACKNUM, TagName.TRACKTOTAL, FirstItem),
    PairTag('disk', TagName.DISCNUM, TagName.DISCTOTAL, FirstItem)
]
# Mappings for Ogg Vorbis tagging container.
OggReadMapping = [
    PictureOut('metadata_block_picture', VorbisCover),
    MoveTag('album', TagName.ALBUM, ToStr),
    MoveTag('date', TagName.DATE, FirstItem, ToInt(notzero=True)),
    MoveTag('grouping', TagName.GROUPING, ToStr),
    MoveTag('title', TagName.TITLE, ToStr),
    MoveTag('artist', TagName.ARTIST, SplitStr(sep=[',', '&', '/'])),
    MoveTag('albumartist', TagName.ALBUMARTIST, SplitStr(sep=[',', '&', '/'])),
    MoveTag('composer', TagName.COMPOSER, SplitStr(sep=[',', '&', '/'])),
    MoveTag('genre', TagName.GENRE, SplitStr(sep=[',', '/'])),
    MoveTag('label', TagName.LABEL, ToStr),
    MoveTag('tracknumber', TagName.TRACKNUM, FirstItem, ToInt(notzero=True)),
    MoveTag('tracktotal', TagName.TRACKTOTAL, FirstItem, ToInt(notzero=True)),
    MoveTag('totaltracks', TagName.TRACKTOTAL, FirstItem, ToInt(notzero=True)),
    MoveTag('discnumber', TagName.DISCNUM, FirstItem, ToInt(notzero=True)),
    MoveTag('disctotal', TagName.DISCTOTAL, FirstItem, ToInt(notzero=True)),
    MoveTag('totaldisks', TagName.DISCTOTAL, FirstItem, ToInt(notzero=True))
]
# Mapping for writing data into ID3 tagging container.
MP3WriteMapping = Mapping(
    PictureIn('APIC', ToApic),
    MoveTag(TagName.ALBUM, 'TALB', ToStr, ToList, ID3In(cls=id3.TALB)),
    MoveTag(TagName.DATE, 'TDRC', ToInt(notzero=True), ToList,
            ID3In(cls=id3.TDRC)),
    MoveTag(TagName.GROUPING, 'GRP1', ToStr, ToList, ID3In(cls=id3.GRP1)),
    MoveTag(TagName.GROUPING, 'TIT1', ToStr, ToList, ID3In(cls=id3.TIT1)),
    MoveTag(TagName.TITLE, 'TIT2', ToStr, ToList, ID3In(cls=id3.TIT2)),
    MoveTag(TagName.ARTIST, 'TPE1', ToStr(sep=', '), ToList,
            ID3In(cls=id3.TPE1)),
    MoveTag(TagName.ALBUMARTIST, 'TPE2', ToStr(sep=', '), ToList,
            ID3In(cls=id3.TPE2)),
    MoveTag(TagName.COMPOSER, 'TCOM', ToStr(sep=', '), ToList,
            ID3In(cls=id3.TCOM)),
    MoveTag(TagName.GENRE, 'TCON', ToStr(sep=', '), ToList,
            ID3In(cls=id3.TCON)),
    MoveTag(TagName.LABEL, 'TPUB', ToStr, ToList, ID3In(cls=id3.TPUB)),
    ToPairTag(TagName.TRACKNUM, TagName.TRACKTOTAL, 'TRCK', ToStr(sep='/'),
              ToList, ID3In(cls=id3.TRCK)),
    ToPairTag(TagName.DISCNUM, TagName.DISCTOTAL, 'TPOS', ToStr(sep='/'),
              ToList, ID3In(cls=id3.TPOS)),
    comment=['^COMM'], legal=['^TCOP$', '^TOWN$', '^TPRO$'], lyrics=['^USLT'],
    require=['^TMOO$', '^PCNT$', '^POPM'], url=['^W[A-Z]{3}'], user=['^TXXX']
)
# Mapping for writing data into MPEG-4 Audio tagging container.
MP4WriteMapping = Mapping(
    PictureIn('covr', ToMp4Cover, ToList),
    MoveTag(TagName.ALBUM, '\xa9alb', ToStr, ToList),
    MoveTag(TagName.DATE, '\xa9day', ToInt(notzero=True), ToStr, ToList),
    MoveTag(TagName.GROUPING, '\xa9grp', ToStr, ToList),
    MoveTag(TagName.TITLE, '\xa9nam', ToStr, ToList),
    MoveTag(TagName.ARTIST, '\xa9ART', ToStr(sep=', '), ToList),
    MoveTag(TagName.ALBUMARTIST, 'aART', ToStr(sep=', '), ToList),
    MoveTag(TagName.COMPOSER, '\xa9wrt', ToStr(sep=', '), ToList),
    MoveTag(TagName.GENRE, '\xa9gen', ToStr(sep=', '), ToList),
    ToPairTag(TagName.TRACKNUM, TagName.TRACKTOTAL, 'trkn', ToListFirstTuple),
    ToPairTag(TagName.DISCNUM, TagName.DISCTOTAL, 'disk', ToListFirstTuple),
    legal=['^cprt$', 'LICENSE$'], lyrics=['^.lyr$']
)
# Mapping for writing data into Ogg Vorbis tagging container.
OggWriteMapping = Mapping(
    PictureIn('metadata_block_picture', ToVorbisCover, ToList),
    MoveTag(TagName.ALBUM, 'album', ToStr, ToList),
    MoveTag(TagName.DATE, 'date', ToInt(notzero=True), ToStr, ToList),
    MoveTag(TagName.GROUPING, 'grouping', ToStr, ToList),
    MoveTag(TagName.TITLE, 'title', ToStr, ToList),
    MoveTag(TagName.ARTIST, 'artist', ToStr(sep=', '), ToList),
    MoveTag(TagName.ALBUMARTIST, 'albumartist', ToStr(sep=', '), ToList),
    MoveTag(TagName.COMPOSER, 'composer', ToStr(sep=', '), ToList),
    MoveTag(TagName.GENRE, 'genre', ToStr(sep=', '), ToList),
    MoveTag(TagName.LABEL, 'label', ToStr, ToList),
    MoveTag(TagName.TRACKNUM, 'tracknumber', ToInt(notzero=1), ToStr, ToList),
    MoveTag(TagName.TRACKTOTAL, 'tracktotal', ToInt(notzero=1), ToStr, ToList),
    MoveTag(TagName.TRACKTOTAL, 'totaltracks', ToInt(notzero=1), ToStr,
            ToList),
    MoveTag(TagName.DISCNUM, 'discnumber', ToInt(notzero=1), ToStr, ToList),
    MoveTag(TagName.DISCTOTAL, 'disctotal', ToInt(notzero=1), ToStr, ToList),
    MoveTag(TagName.DISCTOTAL, 'totaldisks', ToInt(notzero=1), ToStr, ToList),
    legal=['^copyright', '^license'], require=['^mrat', '^mood', '^rating'],
    user=['^contact', '^website'], lyrics=['^lyrics']
)


def _resolve_audiotype(audiofile):
    """
    Args:
        audiofile (mutage.FileType): Media information.

    Returns:
        tuple: A list of rules to move values from one container to another.

    Raises:
        exceptions.FileNotSupportedError: If mapping not defined.
    """
    if isinstance(audiofile, mp3.MP3):
        return AudioType.MP3, MP3ReadMapping, MP3WriteMapping
    elif isinstance(audiofile, mp4.MP4):
        return AudioType.MP4, MP4ReadMapping, MP4WriteMapping
    elif isinstance(audiofile, ogg.OggFileType):
        return AudioType.OGG, OggReadMapping, OggWriteMapping
    else:
        raise exceptions.FileTypeNotSupportedError(audiofile.filename)


def _drop_tags(target, *regexps):
    """Removes tags which match one of the regular expressions."""

    for tagname in list(target.keys()):
        for _ in (x for x in regexps if re.search(x, tagname)):
            try:
                del target[tagname]
            except KeyError:
                pass
            break


def _open(path):
    """Returns Mutagen FileType that contains audio stream info and tags.

    Raises:
        exceptions.NotAnAudioFileError: Invalid file format.
    """
    try:
        fileobj = File(path)
        if fileobj is None:
            raise MutagenError
        if getattr(fileobj, 'tags', None) is None:
            fileobj.add_tags()
        return fileobj
    except (AttributeError, MutagenError):
        raise exceptions.NotAnAudioFileError(path)


def from_file(path):
    """
    Args:
        path (os.PathLike): Audio file to be processed.

    Returns:
        tuple: Media file components.
    """
    audio = _open(os.fspath(path))
    mediatype, mapping = _resolve_audiotype(audio)[:2]
    mediainfo = streams.AudioStream(
        channels=getattr(audio.info, 'channels', 0),
        bit_rate=getattr(audio.info, 'bitrate', 0),
        duration=getattr(audio.info, 'lehgth', 0),
        sample_rate=getattr(audio.info, 'sample_rate', 0))
    metadata = streams.Metadata()
    for rule in mapping:
        rule(audio.tags, metadata)
    return mediatype, mediainfo, metadata


def export(path, metadata, **kwargs):
    """Writes metadata tags to the audio file."""
    audio = _open(os.fspath(path))
    mapping = _resolve_audiotype(audio)[2]
    # Drop useless tags
    useless = ['require'] + kwargs.get('drop', [])
    for namespace in useless:
        _drop_tags(audio.tags, *mapping.get_useless(namespace))
    # Save metadata tags
    for rule in _resolve_audiotype(audio)[2]:
        rule(metadata, audio.tags)
    audio.save()


def probe(path):
    """
    Args:
        path (os.PathLike): Audio file to be probed.

    Returns:
        dict: Audio stream properties.
    """
    audio = _open(os.fspath(path))
    return dict(
        channels=getattr(audio.info, 'channels', 0),
        bit_rate=getattr(audio.info, 'bitrate', 0),
        duration=getattr(audio.info, 'lehgth', 0),
        sample_rate=getattr(audio.info, 'sample_rate', 0))
