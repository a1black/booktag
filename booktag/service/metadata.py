"""Module defines functions to retrieve metadata from media files.

This module does not resolve symbolic links. When reading a symbolic
link functions will collect information about the link itself rather then
the link reference.
"""
import io
import os
import stat

from PIL import Image

from booktag import exceptions
from booktag.api import mutagenapi
from booktag.api import pillowapi
from booktag.utils import ftstat


def fstat(path):
    """Returns file type and size."""
    ft_mode = ftstat.ft_mode(path)
    if not ft_mode:
        raise exceptions.FileNotSupportedError(
            'Neither file nor directory: {}'.format(path))
    stat = os.stat(path, follow_symlinks=False)
    return dict(st_size=getattr(stat, 'st_size', 0), ft_mode=ft_mode)


def image(image_file):
    """Returns image information.

    Args:
        image_file: A filename or raw image.

    Returns:
        dict: Image size and type.
    """
    try:
        return pillowapi.read_meta(image_file)
    except IsADirectoryError:
        return dict(ft_mode=ftstat.S_IFDIR)
    except exceptions.FileIsTrashError:
        return dict(ft_flag=ftstat.F_TODEL)
    except exceptions.FileNotSupportedError:
        return dict(ft_flag=ftstat.f_NOSUP)


def audio(audio_file):
    """Returns audio file metadata.

    Args:
        audio_file (str): Path to an audio file.
    Returns:
        dict: Tag list and audio stream length, bitrate, etc.
    """
    try:
        return mutagenapi.read_meta(audio_file)
    except IsADirectoryError:
        return dict(ft_mode=ftstat.S_IFDIR)
    except exceptions.FileNotSupportedError:
        return dict(ft_flag=ftstat.f_NOSUP)


# vim: ts=4 sw=4 sts=4 et ai
