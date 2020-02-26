import copy
import io
import itertools
import hashlib
import math
import sys

from PIL import Image, ImageFilter

from booktag import exceptions
from booktag import osutils
from booktag.constants import TagName


def _list_frame(value):
    """
    Returns:
        list: Value converted to a list.
    """
    try:
        return [value] if isinstance(value, (str, bytes)) else list(value)
    except TypeError:
        return [value]


def _natural_int(value):
    """
    Returns:
         int: Natural number, or None if value is zero.
    """
    natint = int(value)
    if natint == 0:
        natint = None
    elif natint < 0:
        raise ValueError('invalid literal for natural int: {0}'.format(value))
    return natint


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

    def __bool__(self):
        return self._data is not None and len(self._data)

    def __str__(self):
        return '{0}, {1} bytes, {2}x{3}'.format(self.mime, len(self),
                                                *self.dimensions)

    def __len__(self):
        return len(self._data)

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

    def _resize(self, image, width, height):
        """
        Args:
            image (Image.Image): Original image.
            width (int): New image width.
            height (int): New image height.

        Returns:
            Image.Image: Resized PIL image object.
        """
        w = int(round(width, -1) if math.log10(width) >= 2 else width)
        h = int(round(height, -1) if math.log10(height) >= 2 else height)
        # Increase sharpness of image after resizing.
        unsharp = ImageFilter.UnsharpMask(radius=1.5, percent=70, threshold=5)
        resized = image.resize((w, h), resample=Image.LANCZOS).filter(unsharp)
        resized.format = self.format
        return resized

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
            width = int(self.width * args[0])
            height = int(self.height * args[0])
        elif len(args) == 2:
            width, height = args
        else:
            raise TypeError('resize() takes at most 2 positional arguments but'
                            '{0} were given'.format(len(args)))
        resized = self._resize(self._make_pil(), width, height)
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

    def square(self, minsize, maxsize):
        """Clips square area from the image."""
        image = None
        short_edge = sorted(self.dimensions)[0]
        # Resize image to fit size restrictions
        if short_edge < minsize:
            dx = minsize / short_edge
            image = self._resize(
                self._make_pil(), self.width * dx, self.height * dx)
            short_edge = sorted(image.size)[0]
        elif short_edge > maxsize:
            dx = maxsize / short_edge
            image = self._resize(
                self._make_pil(), self.width * dx, self.height * dx)
            short_edge = sorted(image.size)[0]
        # Crop image to square area with side equals to shortest image edge
        if image is not None:
            dx = (image.size[0] - short_edge) // 2
            dy = (image.size[1] - short_edge) // 2
            dsize = (dx + short_edge, dy + short_edge)
            if dsize < image.size:
                image = image.crop(dx, dy, *dsize)
        # Save changes if any were made
        if image is not None:
            image.format = self.format
            self._export_pil(image)

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
        elif osutils.is_image(path, follow_symlinks=False):
            source = open(path, 'rb')
        else:
            raise exceptions.NotAnImageFileError(path)
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
        TagName.ALBUMSORT: _natural_int,
        TagName.ARTIST: _list_frame,
        TagName.COMMENT: str,
        TagName.COMPOSER: _list_frame,
        TagName.DATE: _natural_int,
        TagName.DISCNUM: _natural_int,
        TagName.DISCTOTAL: _natural_int,
        TagName.GENRE: _list_frame,
        TagName.GROUPING: str,
        TagName.LABEL: str,
        TagName.ORIGINALDATE: _natural_int,
        TagName.TITLE: str,
        TagName.TRACKNUM: _natural_int,
        TagName.TRACKTOTAL: _natural_int
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

    def copy(self):
        return self.__class__({k: copy.copy(v) for k, v in self.items()})

    def dump(self):
        return {k: copy.copy(v) for k, v in self.items()}

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, *args, **kwargs):
        for data in itertools.chain(args, (kwargs,)):
            for key, value in data.items():
                self[key] = value
