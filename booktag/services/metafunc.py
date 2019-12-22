import functools

from booktag import exceptions
from booktag.api import mutagenapi
from booktag.api import pillowapi
from booktag.app import filenode
from booktag.utils import ftstat


def read_dir_meta(dirname, **kwargs):
    """
    Retruns mapping of properties that accumulate corresponding values of
    entries in the directory.
    """
    return dict(ft_mode=ftstat.S_IFDIR,
                length=filenode.AggregatorProp('length'),
                st_size=filenode.AggregatorProp('st_size'))


def read_audio_meta(audiofile, **kwargs):
    """Returns metadata stored in the audio file.

    Args:
        audiofile (:class:`os.PathLike`): A tree node object or pathname.

    Returns:
        dict: Collection of audio container attributes.

        Includes content type, tagging container, audio length, bitrate and
        number of chanels.
    """
    try:
        return mutagenapi.read_meta(audiofile, **kwargs)
    except IsADirectoryError:
        return read_dir_meta(audiofile)
    except exceptions.FileNotSupportedError:
        ft_mode = getattr(audiofile, 'ft_mode', 0) | ftstat.F_NOSUP
        return dict(ft_mode=ft_mode)


def read_image_meta(imagefile, **kwargs):
    """Returns image properties.

    Args:
        imagefile (:class:`os.PathLike`): A tree node or pathname.

    Returns:
        dict: Collection of image container attributes.

        Includes content type, image dimensions.
    """
    try:
        return pillowapi.read_meta(imagefile, **kwargs)
    except IsADirectoryError:
        return read_dir_meta(imagefile)
    except exceptions.FileIsTrashError:
        ft_mode = getattr(imagefile, 'ft_mode', 0) | ftstat.F_TODEL
        return dict(ft_mode=ft_mode)
    except exceptions.FileNotSupportedError:
        ft_mode = getattr(imagefile, 'ft_mode', 0) | ftstat.F_NOSUP
        return dict(ft_flag=ft_mode)


def is_imagenode(node):
    """Tests if `node` is an image file."""
    return ftstat.S_ISIMG(getattr(node, 'ft_mode', 0))


def is_audionode(node):
    """Tests if `node` is an audio file."""
    return ftstat.S_ISAUD(getattr(node, 'ft_mode', 0))


def is_supported(node):
    """Tests if `node` is not flagged as unsupported."""
    return not(getattr(node, 'ft_mode', 0) & ftstat.F_NOSUP)


def is_deleted(node):
    """Tests if `node` is not marked for deletion."""
    return not(getattr(node, 'ft_mode', 0) & ftstat.F_TODEL)


def not_decorator(func):
    """Returns wrapper function that negates result of `func`."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return not func(*args, **kwargs)

    return wrapper


# vim: ts=4 sw=4 sts=4 et ai
