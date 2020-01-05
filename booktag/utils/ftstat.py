"""Constatns and functions for creating/interpreting bits that describes
file format and application specific flags.

This module is simular to :module:`stat`.
"""
import os
import re
import stat

import magic


# File flags (limited to 12 flags).
F_TODEL = 0o0001  # file marked to be deleted
F_NOSUP = 0o0002  # file format is not supported

# File type as in module stat, occupied range:
# S_IFIFO  = 0o010000
# S_IFSOCK = 0o160000
S_IFDIR = stat.S_IFDIR
S_IFREG = stat.S_IFREG
S_IFLNK = stat.S_IFLNK
S_IFMT = stat.S_IFMT

# Constants for various content types.
S_IFAUD = 0o0200000  # audio
S_IFIMG = 0o0400000  # digital image
S_IFBOK = 0o0600000  # e-book
# S_IFRES = 0o1600000

# Constants for various file formats.
S_IFMP3 = 0o02000000
S_IFMP4 = 0o04000000
S_IFOGG = 0o06000000
S_IFFLC = 0o10000000
S_IFWAV = 0o12000000
S_IFJPG = 0o14000000
S_IFPNG = 0o16000000
S_IFPDF = 0o22000000
S_IFEPB = 0o24000000
S_IFFB2 = 0o26000000
# S_IFRES = 0o76000000


def F_FSET(mode):
    """Returns file flag bits."""
    try:
        return mode & 0o7777
    except TypeError:
        raise TypeError('an integer is required')


def S_IFCT(mode):
    """Returns the portion of the file's mode that discribes
    the content type."""
    try:
        return mode & 0o1600000
    except TypeError:
        raise TypeError('an integer is required')


def S_IFFF(mode):
    """Returns the portion of the file's mode that discribes
    the file format."""
    try:
        return mode & 0o76000000
    except TypeError:
        raise TypeError('an integer is required')


def S_ISDIR(mode):
    """Returns True if mode is from a directory."""
    return stat.S_ISDIR(mode)


def S_ISREG(mode):
    """Returns True if mode is from a regular file."""
    return stat.S_ISREG(mode)


def S_ISLNK(mode):
    """Returns True if mode is from a symbolic link."""
    return stat.S_ISLNK(mode)


def S_ISAUD(mode):
    """Returns True if mode is from audio file."""
    return S_IFCT(mode) == S_IFAUD


def S_ISIMG(mode):
    """Returns True if mode is from digital image file."""
    return S_IFCT(mode) == S_IFIMG


def S_ISBOK(mode):
    """Returns True if mode is from e-book file."""
    return S_IFCT(mode) == S_IFBOK


def S_ISMP3(mode):
    """Returns True if mode is from MP3 file."""
    return S_IFFF(mode) == S_IFMP3


def S_ISMP4(mode):
    """Returns True if mode is from MP4 audio file."""
    return S_IFFF(mode) == S_IFMP4


def S_ISOGG(mode):
    """Returns True if mode is from OGG file."""
    return S_IFFF(mode) == S_IFOGG


def S_ISFLC(mode):
    """Returns True if mode is from FLAC file."""
    return S_IFFF(mode) == S_IFFLC


def S_ISWAV(mode):
    """Returns True if mode is from WAV Pack file."""
    return S_IFFF(mode) == S_IFWAV


def S_ISJPG(mode):
    """Returns True if mode is from JPEG file."""
    return S_IFFF(mode) == S_IFJPG


def S_ISPNG(mode):
    """Returns True if mode is from PNG file."""
    return S_IFFF(mode) == S_IFPNG


def S_ISPDF(mode):
    """Returns True if mode is from PDF file."""
    return S_IFFF(mode) == S_IFPDF


def S_ISEPB(mode):
    """Returns True if mode is from EPUB file."""
    return S_IFFF(mode) == S_IFEPB


def S_ISFB2(mode):
    """Returns True if mode is from FB2 file."""
    return S_IFFF(mode) == S_IFFB2


def ft_extension(mode):
    """Returns extension for a file format described by the `mode`.

    Args:
        mode (int): File mode.

    Returns:
        :obj:`tuple` of :obj:`str`: Tuple of filename extensions.
    """
    if S_ISMP3(mode):
        return ('.mp3',)
    elif S_ISMP4(mode):
        return ('.m4a', '.mp4')
    elif S_ISOGG(mode):
        return ('.ogg',)
    elif S_ISFLC(mode):
        return ('.flac',)
    elif S_ISWAV(mode):
        return ('.wav',)
    elif S_ISJPG(mode):
        return ('.jpg', '.jpeg', '.jpe')
    elif S_ISPNG(mode):
        return ('.png',)
    elif S_ISEPB(mode):
        return ('.epub',)
    elif S_ISFB2(mode):
        return ('.fb2',)
    elif S_ISPDF(mode):
        return ('.pdf',)
    else:
        return ('')


def ft_name(mode):
    """Returns that contains names of file type, content type and format."""
    ftname = ((S_ISDIR(mode) and 'dir') or (S_ISREG(mode) and 'file')
              or (S_ISLNK(mode) and 'symlink') or None)
    ctname = ((S_ISAUD(mode) and 'audio') or (S_ISBOK(mode) and 'book')
              or (S_ISIMG(mode) and 'image') or None)
    ext = ft_extension(mode)[0]
    fnname = ext[1:] if ext else None
    return (ftname, ctname, fnname)


def ft_mode(path, stats=None):
    """Returns integer that describes file type and file format."""
    if stats is None:
        stats = os.stat(path, follow_symlinks=False)
    mode = 0
    if stat.S_ISLNK(stats.st_mode):
        mode |= stat.S_IFLNK
    elif stat.S_ISDIR(stats.st_mode):
        mode |= stat.S_IFDIR
    elif stat.S_ISREG(stats.st_mode):
        mode |= stat.S_IFREG
        mime = magic.from_file(path, mime=True)
        # Determine content type.
        if mime.startswith('audio/') or mime == 'application/octet-stream':
            mode |= S_IFAUD
        elif mime.startswith('image/'):
            mode |= S_IFIMG
        # Determine file format.
        if re.match(r'^audio/(?:x-)?(?:mp[23]|mpeg)$', mime):
            mode |= S_IFMP3
        elif re.match(r'^audio/(?:x-)?(?:m4a|mp4|mpeg4)$', mime):
            mode |= S_IFMP4
        elif re.match(r'^audio/(?:x-)?(?:ogg)?flac$', mime):
            mode |= S_IFFLC
        elif mime.startswith('audio/ogg'):
            mode |= S_IFOGG
        elif re.match(r'^audio/(?:x-)?wav$', mime):
            mode |= S_IFWAV
        elif mime == 'image/jpeg':
            mode |= S_IFJPG
        elif mime == 'image/png':
            mode |= S_IFPNG
        elif mime == 'application/epub+zip':
            mode |= S_IFBOK | S_IFEPB
        elif mime == 'application/fb2+xml':
            mode |= S_IFBOK | S_IFFB2
        elif mime == 'application/pdf':
            mode |= S_IFBOK | S_IFPDF

    return mode


# vim: ts=4 sw=4 sts=4 et ai
