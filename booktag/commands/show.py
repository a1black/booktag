import logging
import sys

import humanize

from booktag import exceptions
from booktag import mutagenfacade
from booktag.mediafile import AudioFile
from booktag.settings import settings


def _init_logger():
    logger = logging.getLogger('show')
    logger.level = logging.INFO
    handler = logging.StreamHandler(stream=sys.stdout)
    formater = logging.Formatter('%(message)s')
    handler.setFormatter(formater)
    handler.level = logging.INFO
    logger.addHandler(handler)
    return logger


def _format_metadata_tag(key, value):
    key = key.strip(' :')
    if hasattr(value, 'pprint'):
        return value.pprint()
    elif isinstance(value, (list, tuple)) and len(value) == 1:
        value = str(value[0])
    else:
        value = str(value)
    return '{0:12.12s}  {1:.64s}'.format(key, value)


def _format_timedelta(timedelta):
    """Returns human friendly audio stream duration."""
    hours, seconds = divmod(timedelta, 3600)
    minutes, seconds = divmod(seconds, 60)
    return '{0:02.0f}:{1:02.0f}:{2:02.0f}'.format(hours, minutes, seconds)


def main(*paths):
    logger = _init_logger()
    for path in paths:
        try:
            # Process audio file
            afile = AudioFile.from_file(path)
            if settings.get('metadata.show.raw'):
                araw = mutagenfacade.read_raw(path)
            else:
                araw = {}
            bitrate = humanize.naturalsize(
                afile.audio.bit_rate, format='%.0f').lower() + 'ps'
            duration = _format_timedelta(afile.audio.duration)
            # Print audio stream info
            logger.info('=====\n{0} ({1}): {2} {3}, {4}'.format(
                afile.path, humanize.naturalsize(afile.size, gnu=True),
                afile.format.title(), bitrate, duration
            ))
            # Print processed metadata tags
            if afile.metadata:
                logger.info('Processed metadata tags')
            for key, val in sorted(afile.metadata.items(), key=lambda x: x[0]):
                logger.info(_format_metadata_tag(key, val))
            if araw:
                logger.info('\nRaw metadata tags')
            for key, val in sorted(araw.items(), key=lambda x: x[0]):
                logger.info(_format_metadata_tag(key, val))
        except exceptions.NotAnAudioFileError:
            logger.warning("file not supported or not an audio: '{0}'".format(
                path))
