import errno
import os


class AppBaseError(Exception):
    """Base application error."""


class FileError(OSError, AppBaseError):
    """Application extension of :class:`OSError`.

    Args:
        path (str): Path which caused an error.
        msg (str): An error message.
        err (:obj:`int`, optional): Error code.
    """

    def __init__(self, path, msg, err=None):
        args = [] if errno is None else [err]
        args.append(msg if msg else 'Problematic path')
        if path:
            args.append(os.fspath(path))
        super().__init__(*args)


class IsASymlinkError(FileError):
    """Raised when the application encounters a symbol link."""

    def __init__(self, path):
        super().__init__(path, 'Symbol link encountered', errno.EAGAIN)


class FileNotSupportedError(AppBaseError):
    """Raised when file cann't be processed by the application."""


class FileIsTrashError(AppBaseError):
    """Raised when file should be deleted."""


# vim: ts=4 sw=4 sts=4 et ai
