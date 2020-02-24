import errno
import os


class AppBaseError(Exception):
    """Base application error."""


class CliArgumentError(AppBaseError):
    """Raised when user provides invalid value for command-line argument."""

    def __init__(self, cmd, msg):
        super().__init__(msg)
        self.command = cmd


class FileTypeNotSupportedError(AppBaseError, OSError):
    """Raised when file cann't be processed by the application."""

    def __init__(self, filename, msg=None):
        super().__init__(errno.ENOSYS,
                         msg or 'Content type is not supported',
                         os.fsdecode(filename) if filename else None)


class NotAnAudioFileError(AppBaseError, OSError):
    """
    Raised when a file operation is requested on something which is not audio.
    """

    def __init__(self, filename):
        super().__init__(errno.EIO, 'Not an audio',
                         os.fsdecode(filename) if filename else None)


class NotAnImageFileError(AppBaseError, OSError):
    """
    Raised when a file operation is requested on something which is not image.
    """

    def __init__(self, filename):
        super().__init__(errno.EIO, 'Not an image',
                         os.fsdecode(filename) if filename else None)
