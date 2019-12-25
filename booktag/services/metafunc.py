"""
TODO:
    * :func:`.write_audio_meta`: Write handler in case if tags is None
"""
from booktag import exceptions
from booktag.api import mutagenapi
from booktag.api import pillowapi
from booktag.app import filenode
from booktag.utils import ftstat


def write_audio_meta(node, **kwargs):
    """Writes mapping of audio tags into the file `node`.

    Args:
        audiofile (:class:`os.PathLike`): A tree node object.
    """
    try:
        mutagenapi.write_meta(node, node.props.tags, **kwargs)
    except exceptions.FileNotSupportedError:
        ft_mode = getattr(node, 'ft_mode', 0) | ftstat.F_NOSUP
        node.props.update(ft_mode=ft_mode)


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


def get_filetype(node):
    return ftstat.S_IFMT(getattr(node, 'ft_mode', 0))


def is_dir_node(node):
    """Tests if `node` is a directory."""
    return ftstat.S_ISDIR(getattr(node, 'ft_mode', 0))


def is_image_node(node):
    """Tests if `node` is an image file."""
    return ftstat.S_ISIMG(getattr(node, 'ft_mode', 0))


def is_audio_node(node):
    """Tests if `node` is an audio file."""
    return ftstat.S_ISAUD(getattr(node, 'ft_mode', 0))


def is_supported(node):
    """Tests if `node` is not flagged as unsupported."""
    return not(getattr(node, 'ft_mode', 0) & ftstat.F_NOSUP)


def is_deleted(node):
    """Tests if `node` is not marked for deletion."""
    return not(getattr(node, 'ft_mode', 0) & ftstat.F_TODEL)


# vim: ts=4 sw=4 sts=4 et ai
