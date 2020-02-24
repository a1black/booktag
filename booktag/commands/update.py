import collections
import errno
import gc

import natsort
import tqdm

from booktag import exceptions
from booktag import logutils
from booktag import find
from booktag import osutils
from booktag.settings import settings
from booktag.constants import TagName
from booktag.mediafile import AudioFile
from booktag.streams import ImageStream, Metadata


logger = logutils.setup_tqdm_logger('update', settings.get('debug'))


class _CoverPool(collections.UserDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter = {}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._counter[key] = 1

    def __delitem__(self, key):
        if key in self._counter:
            del self._counter[key]
        super().__delitem__(key)

    def add(self, image):
        key = hash(image)
        if key in self:
            self._counter[key] += 1
        else:
            self[key] = image
        return self[key]

    def move(self, from_, to):
        if from_ != to:
            count = self._counter[from_]
            image = self.pop(from_)
            self[to] = image
            self._counter[to] = count

    def max(self):
        try:
            return max(self._counter.items(), key=lambda x: x[1])[0]
        except ValueError:
            return None


class Updater:

    BAR_SIZE = 50
    BAR_FMT = '{l_bar}{bar}| {n_fmt}/{total_fmt}  '

    def __init__(self, sources):
        self._cover_pool = _CoverPool()
        self._audio_queue = collections.deque()
        self._source_paths = sorted(
            sources, key=natsort.natsort_keygen(key=lambda entry: entry.name))

    def _first_pass(self):
        """Finds audio files in first pass over the source files."""
        for path in tqdm.tqdm(self._source_paths, desc='Scan',
                              ncols=self.BAR_SIZE, bar_format=self. BAR_FMT):
            try:
                scaniter = find.FindStatic(path, follow_symlinks=False)
                scaniter.perm('rw').type(find.AUDIO_TYPE).sort(find.NAT_SORT)
                scaniter.exec(AudioFile.from_file)
                logger.info("scan for audio files: '{0}'".format(path))
                self._audio_queue.extend(scaniter)
            except NotADirectoryError:
                try:
                    self._audio_queue.append(AudioFile.from_file(path))
                except exceptions.NotAnAudioFileError:
                    logger.warning("not an audio file: '{0}'".format(path))
        if not len(self._audio_queue):
            raise RuntimeError('no audio files find')

    def _second_pass(self):
        """Loads metadata tags in second pass over source files."""
        for file in tqdm.tqdm(self._audio_queue, desc='Load meta',
                              ncols=self.BAR_SIZE, bar_format=self.BAR_FMT):
            logger.info("load metadata tag: '{0}'".format(file.path))
            # Process embedded cover picture
            cover_image = file.cover
            if cover_image is not None:
                file.cover = self._cover_pool.add(cover_image)
            else:
                del file.cover

    def _load_external_cover(self):
        """Returns external image that will be used as album cover art."""
        cover: ImageStream = settings.get(f'album_metadata.{TagName.COVER}')
        if cover is None and not self._cover_pool:
            # TODO: Implement loading image from Google Images service
            pass
        if cover:
            cover.jpeg()
            cover.square(settings.get('metadata.cover.minsize', 500),
                         settings.get('metadata.cover.maxsize', 1000))
        return cover

    def _load_embedded_cover(self):
        image_hashes = list(self._cover_pool.keys())
        for old_hash in image_hashes:
            image: ImageStream = self._cover_pool[old_hash]
            image.jpeg()
            image.square(settings.get('metadata.cover.minsize', 500),
                         settings.get('metadata.cover.maxsize', 1000))
            self._cover_pool.move(old_hash, hash(image))
        return self._cover_pool.max()

    def run(self):
        # Discover audio files
        self._first_pass()
        # Load metadata tags
        self._second_pass()
        # Clean up
        gc.collect()
        # Select album cover art
        cover = self._load_external_cover()
        cover_embedded = self._load_embedded_cover() if cover is None else None
        # Set track/disc metadata tags
        meta: dict = settings.get('album_metadata', Metadata()).dump()
        if TagName.TRACKNUM not in meta and TagName.TRACKTOTAL not in meta:
            tracknum = 1
            tracktotal = len(self._audio_queue)
        else:
            tracknum = meta.pop(TagName.TRACKNUM, 1)
            tracktotal = meta.pop(TagName.TRACKTOTAL, 0)
        discnum = meta.pop(TagName.DISCNUM, 0)
        disctotal = meta.pop(TagName.DISCTOTAL, 0)
        # Write new metadata tags
        update_bar = tqdm.tqdm(self._audio_queue, desc='Update',
                               ncols=self.BAR_SIZE, bar_format=self.BAR_FMT)
        for tracknum, file in enumerate(update_bar, start=tracknum):
            logger.info("update metadata tag: '{0}'".format(file.path))
            # Set new tag from configuration, including external cover art
            file.metadata.update(meta)
            if not settings.get('metadata.tags.keeptracknum', False):
                file.metadata[TagName.TRACKNUM] = tracknum
                file.metadata[TagName.TRACKTOTAL] = tracktotal
            if not settings.get('metadata.tags.keepdiscnum', False):
                file.metadata[TagName.DISCNUM] = discnum
                file.metadata[TagName.DISCTOTAL] = disctotal
            # Set cover art using embedded image from another audio file
            if file.cover is None and cover_embedded:
                file.cover = cover_embedded


def main(*paths):
    Updater(paths).run()
