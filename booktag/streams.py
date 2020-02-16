import io
import itertools
import hashlib
import os
import sys

from PIL import Image

from booktag import exceptions
from booktag.constants import TagName


def _list_frame(value):
    """Returns value converted to a list."""
    try:
        return [value] if isinstance(value, (str, bytes)) else list(value)
    except TypeError:
        return [value]


class AudioStream:
    """Audio stream properties.

    Args:
        sample_rate(:obj:`int`, optional): Sound sample rate in Hz.
        bit_rate(:obj:`int`, optional): Bit rate in kilobits per second.
        duration(:obj:`int`, optional): Audio duratoin in seconds.
        channels(:obj:`int`, optional): Number of sound tracks.
        **kwargs: Extra arguments that can be set by prober.
    """

    def __init__(self, *, sample_rate=None, bit_rate=None, duration=None,
                 channels=None, **kwargs):
        self._bit_rate = int(bit_rate or 0)
        self._channels = int(channels or 0)
        self._duration = int(duration or 0)
        self._sample_rate = int(sample_rate or 0)

    @property
    def bit_rate(self):
        """int: Bit rate of the audio stream."""
        return self._bit_rate

    @property
    def channels(self):
        """int: Number of sound tracks in the audio file."""
        return self._channels

    @property
    def duration(self):
        """int: Duration of the audio stream in seconds."""
        return self._duration

    @property
    def sample_rate(self):
        """int: Sample rate of the audio stream."""
        return self._sample_rate


class ImageStream:
    """Embedded picture.

    Args:
        image (bytes): Raw data.
        format (:obj:`str`, optional): Image file format.
        dimensions(:obj:`tuple(int,int)`, optional): Image `(width, height)`.
    """

    JPEG = 'JPEG'
    FLIP_LEFT_RIGHT = Image.FLIP_LEFT_RIGHT
    FLIP_TOP_BOTTOM = Image.FLIP_TOP_BOTTOM
    ROTATE_90 = Image.ROTATE_90
    ROTATE_180 = Image.ROTATE_180
    ROTATE_270 = Image.ROTATE_270

    def __init__(self, image, format, dimensions):
        self._data = image
        self._dimensions = dimensions
        self._format = format
        self._mime = 'image/{0}'.format(format).lower()
        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = hashlib.md5(self._data).hexdigest()
        return self._hash

    def __eq__(self, other):
        if isinstance(other, bytes):
            return hashlib.md5(other).hexdigest() == hash(self)
        else:
            return hash(self) == other

    def _export_pil(self, pil):
        """
        Exports image object to a new byte string.

        Args:
            pil (Image.Image): PIL image object.
        """
        buffer = io.BytesIO()
        pil.save(buffer, format=pil.format, quality=90)
        buffer.seek(0)
        self._data = buffer.read()
        self._dimensions = pil.size
        self._format = pil.format
        self._mime = 'image/{0}'.format(pil.format.lower())
        self._hash = None
        pil.close()

    def _make_pil(self):
        """
        Returns:
            Image.Image: PIL image object.
        """
        return Image.open(io.BytesIO(self.data))

    def flip(self, method=FLIP_LEFT_RIGHT):
        """Flips the image from left to right or from top to bottom."""
        if method in (self.FLIP_LEFT_RIGHT, self.FLIP_TOP_BOTTOM):
            flipped = self._make_pil().transpose(method)
            flipped.format = self.format
        else:
            raise ValueError('unknown flip method: {0}'.format(method))
        self._export_pil(flipped)

    def resize(self, *args):
        """Changes size of the image.

        Args:
            *args: Resize scale or precise image size.
        """
        if len(args) == 1:
            width, height = self.width * args[0], self.height * args[0]
        elif len(args) == 2:
            width, height = args
        else:
            raise TypeError('resize() takes at most 2 positional arguments but'
                            '{0} were given'.format(len(args)))
        resized = self._make_pil().resize((width, height),
                                          resample=Image.BILINEAR)
        resized.format = self.format
        self._export_pil(resized)

    def rotate(self, method=ROTATE_90):
        """Rotates image in 90 degree steps."""
        if method in (self.ROTATE_90, self.ROTATE_180, self.ROTATE_270):
            rotated = self._make_pil().transpose(method)
            rotated.format = self.format
        else:
            raise ValueError('unknown rotation method: {0}'.format(method))
        self._export_pil(rotated)

    def jpeg(self):
        """Converts image to a jpeg format."""
        if self.format != self.JPEG:
            converted = self._make_pil().convert(mode='RGB')
            converted.format = self.JPEG
            self._export_pil(converted)

    @property
    def data(self):
        """bytes: Raw image data."""
        return self._data

    @property
    def format(self):
        """str: Image file format."""
        return self._format

    @property
    def mime(self):
        """str: Image mime type."""
        return self._mime

    @property
    def dimensions(self):
        """tuple(int,int): Image dimentions."""
        return self._dimensions

    @property
    def width(self):
        """int: Image width in pixels."""
        return self.dimensions[0]

    @property
    def height(self):
        """int: Image height in pixels."""
        return self.dimensions[1]

    @classmethod
    def from_file(cls, path):
        """
        Args:
            path: A pathname or a raw image data.

        Returns:
            ImageStream: A new instance of class using content of `path`.
        """
        if isinstance(path, bytes):
            source = io.BytesIO(path)
            path = '<embedded picture>'
        else:
            path = os.fspath(path)
            source = open(path, 'rb')
        try:
            pil: Image.Image = Image.open(source)
            new_instance = cls(b'', '', (0, 0))
            new_instance._export_pil(pil)
            return new_instance
        except (Image.DecompressionBombError, OSError):
            raise exceptions.NotAnImageFileError(path)


class Metadata:
    """Dictionary-like container for storing metadata tags.

    Attributes:
        mapping (dict): Mapping of callable objects which modify value before
            setting it to a corresponding key.

    Args:
        metadata (dict): Collection of tags.
        **kwargs: Metadata tags are of the form 'key=value'.
    """

    mapping = {
        TagName.ALBUM: str,
        TagName.ALBUMARTIST: _list_frame,
        TagName.ARTIST: _list_frame,
        TagName.COMMENT: str,
        TagName.COMPOSER: _list_frame,
        TagName.DATE: int,
        TagName.DISCNUM: int,
        TagName.DISCTOTAL: int,
        TagName.GENRE: _list_frame,
        TagName.GROUPING: str,
        TagName.LABEL: str,
        TagName.ORIGINALDATE: int,
        TagName.TITLE: str,
        TagName.TRACKNUM: int,
        TagName.TRACKTOTAL: int
    }

    def __init__(self, metadata=None, **kwargs):
        super().__setattr__('_data', {})
        self.update(metadata or {}, kwargs)

    def __sizeof__(self):
        return sum(sys.getsizeof(k) + sys.getsizeof(v)
                   for k, v in self.items())

    def __iter__(self):
        return self.keys()

    def __contains__(self, name):
        return name in self._data

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        if value is not None and key in self.mapping:
            value = self.mapping[key](value)
        if value is None:
            del self[key]
        else:
            self._data[key] = value

    def __delitem__(self, key):
        try:
            del self._data[key]
        except KeyError:
            pass

    def __getattr__(self, name):
        """`d.name -> d[name]`."""
        if name in self:
            return self[name]
        raise AttributeError('{0!r} object has no attribute {1!r}'.format(
            type(self).__name__, name))

    def __setattr__(self, name, value):
        """`d.name = value -> d[name] = value`."""
        self[name] = value

    def items(self):
        return iter(self._data.items())

    def keys(self):
        return iter(self._data.keys())

    def clear(self):
        self._data.clear()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, *args, **kwargs):
        for data in itertools.chain(args, (kwargs,)):
            for key, value in data.items():
                self[key] = value
