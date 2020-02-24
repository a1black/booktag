import os
import re

from booktag import exceptions
from booktag import mutagenfacade
from booktag import osutils
from booktag import streams
from booktag.constants import AudioType, TagName


class AudioFile:

    def __init__(self, path, format):
        stat = os.stat(path)
        self._format = AudioType(format)
        self._path = os.fsdecode(path)
        self._size = int(stat.st_size)
        self._audio_stream = None
        self._image_stream = None
        self._metadata = None

    def __fspath__(self):
        return self.path

    def _lazy_load(self):
        aformat, ainfo, ameta = mutagenfacade.from_file(self.path)
        self._audio_stream = ainfo
        self._format = AudioType(aformat)
        self._metadata = ameta

    def export_metadata(self):
        mutagenfacade.export(self, self.metadata)

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

    @cover.deleter
    def cover(self):
        """Removes album cover art."""
        del self.metadata[TagName.COVER]

    @property
    def format(self):
        """str: Audio format."""
        return self._format

    @property
    def metadata(self):
        """streams.Metadata: Metadata tags stored in the file container."""
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
        filetype = osutils.is_audio(path, follow_symlinks=False)
        if not filetype:
            raise exceptions.NotAnAudioFileError(path)
        return cls(path, format=filetype)
