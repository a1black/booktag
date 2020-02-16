import os
import re

import magic

from booktag import exceptions
from booktag import mutagenfacade
from booktag import streams
from booktag.constants import AudioType, PictureType, TagName


class AudioFile:

    def __init__(self, path, format):
        stat = os.stat(path)
        self._format = AudioType(format)
        self._path = os.fsdecode(path)
        self._size = int(stat.st_size)
        self._audio_stream = None
        self._image_stream = None
        self._metadata = None

    def _lazy_load(self):
        aformat, ainfo, ameta = mutagenfacade.from_file(self.path)
        self._audio_stream = ainfo
        self._format = AudioType(aformat)
        self._metadata = ameta

    @property
    def audio(self):
        """streams.AudioStream: Properties of audio stream in the file."""
        if self._audio_stream is None:
            self._lazy_load()
        return self._audio_stream

    @property
    def cover(self):
        """streams.ImageStream: Embedded cover picture."""
        metadata = self.metadata
        return metadata.get(TagName.COVER, None)

    @cover.setter
    def cover(self, picture):
        """Sets album cover art."""
        metadata = self.metadata
        if picture is None:
            del metadata[TagName.COVER]
        elif isinstance(picture, bytes):
            metadata[TagName.COVER] = streams.ImageStream.from_file(picture)
        elif isinstance(picture, streams.ImageStream):
            metadata[TagName.COVER] = picture
        else:
            raise TypeError('invalid type of image data: {0}'.format(
                type(picture).__name__))

    @property
    def format(self):
        """str: Audio format."""
        return self._format

    @property
    def metadata(self):
        """Metadata: Metadata tags stored in the file container."""
        if self._metadata is None:
            self._lazy_load()
        return self._metadata

    @property
    def name(self):
        """str: Name of the file without extension."""
        basename = os.path.basename(self.path)
        return re.sub(r'\.(mp3|mp4|m4a|ogg)$', '', basename, flags=re.I)

    @property
    def path(self):
        """str: Pathname to the audio file."""
        return self._path

    @property
    def size(self):
        """int: File size in bytes."""
        return self._size

    @classmethod
    def from_file(cls, path):
        """
        Returns:
            AudioFile: A new instance of a class.
        """
        mime = magic.from_file(os.fsdecode(path), mime=True)
        if re.match('^audio/(?:x-)?(?:mp[23]|mpeg)$', mime):
            audio_format = AudioType.MP3
        elif re.match('^audio/(?:x-)?(?:m4a|mp4|mpeg4)$', mime):
            audio_format = AudioType.MP4
        # elif re.match(r'^audio/(?:x-)?(?:ogg)?flac$', mime):
        #     audio_format = None
        elif mime == 'audio/ogg':
            audio_format = AudioType.OGG
        else:
            raise exceptions.NotAnAudioFileError(path)
        return cls(path, format=audio_format)
