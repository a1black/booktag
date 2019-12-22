import io
import os

from PIL import Image

from booktag import exceptions
from booktag.utils import ftstat

FLIP_LEFT_RIGHT = Image.FLIP_LEFT_RIGHT
FLIP_TOP_BOTTOM = Image.FLIP_TOP_BOTTOM
ROTATE_90 = Image.ROTATE_90
ROTATE_180 = Image.ROTATE_180
ROTATE_270 = Image.ROTATE_270


def open(image):
    """Returns PIL Image object.

    Args:
        image: A filename or the raw image data.
    """
    try:
        if isinstance(image, Image.Image):
            return image
        elif isinstance(image, bytes):
            source = io.BytesIO(image)
        else:
            source = os.fspath(image)
        return Image.open(source)
    except Image.DecompressionBombError:
        raise exceptions.FileIsTrashError
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        raise
    except OSError:
        raise exceptions.FileNotSupportedError


def save(image):
    """Saves modifications made to PIL Image object.

    Returns:
        ``bytes`` for in-memory data or a filename.
    """
    try:
        image.save(image.filename, format=image.format)
        return image.filename
    except AttributeError:
        buffer = io.BytesIO()
        image.save(buffer, format=image.format)
        return buffer


def read_meta(image, **kwargs):
    """Returns image attributes.

    Args:
        image: A filename or the raw image data.

    Retruns:
        dict: Image type and dimensions.
    """
    imgobj = open(image)
    width, height = imgobj.size
    ft_mode = ftstat.S_IFREG | ftstat.S_IFIMG
    if imgobj.format == 'JPEG':
        ft_mode |= ftstat.S_IFJPG
    elif imgobj.format == 'PNG':
        ft_mode |= ftstat.S_IFPNG
    return dict(width=width, height=height, mode=imgobj.mode,
                ft_mode=ft_mode)


def flip(image, method=FLIP_LEFT_RIGHT):
    """Flips the image from left to right or from top to bottom."""
    imgobj = open(image)
    if method == FLIP_LEFT_RIGHT:
        flipped = imgobj.transpose(Image.FLIP_LEFT_RIGHT)
    elif method == FLIP_TOP_BOTTOM:
        flipped = imgobj.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError('unknown flip method: {0}'.format(method))
    flipped.filename = imgobj.filename
    flipped.format = imgobj.format
    return flipped if isinstance(image, Image.Image) else save(flipped)


def resize(image, *args):
    """Changes size of the image.

    Args:
        *args: Single value for scaling or two values for precise image size.
    """
    imgobj = open(image)
    if len(args) == 1:
        width, height = imgobj.width * args[0], imgobj.height * args[0]
    elif len(args) == 2:
        width, height = args
    else:
        raise TypeError('resize() takes at most 2 positional arguments but {0}'
                        ' were given'.format(len(args)))
    resized = imgobj.resize((width, height), resample=Image.HAMMING)
    resized.filename = imgobj.filename
    resized.format = imgobj.format
    return resized if isinstance(image, Image.Image) else save(resized)


def rotate(image, method=ROTATE_90):
    """Rotates image in 90 degree steps."""
    imgobj = open(image)
    if method == ROTATE_90:
        rotated = imgobj.transpose(Image.ROTATE_90)
    elif method == ROTATE_180:
        rotated = imgobj.transpose(Image.ROTATE_180)
    elif method == ROTATE_270:
        rotated = imgobj.transpose(Image.ROTATE_270)
    else:
        raise ValueError('unknown rotation method: {0}'.format(method))
    rotated.filename = imgobj.filename
    rotated.format = imgobj.format
    return rotated if isinstance(image, Image.Image) else save(rotated)


# vim: ts=4 sw=4 sts=4 et ai
