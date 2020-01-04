import contextlib
import os
import sys
import time
import threading

from booktag import exceptions
from booktag.app import commands
from booktag.services import metafunc
from booktag.services import statistic


class App:
    """Basic script that update metadata without user interaction."""

    def __init__(self):
        self._config = {}
        self._tags = None
        self._view = View()

    def get_config(self):
        return self._config

    def set_config(self, config):
        self._config = config

    def get_tags(self):
        return self._tags

    def set_tags(self, tags):
        self._tags = tags

    def get_view(self):
        return self._view

    def run(self):
        path = self.config.get('path')
        encoding = self.config.get('read.audio.encoding')
        if not (path and (encoding or self.tags)):
            exceptions.HaltError('there is nothing to do, terminate process')
        # Load data
        with self.view.show_wait('Scan path'):
            tree = commands.build_tree(self.config, path)
            # Validate data
            if metafunc.is_dir_node(tree) and not tree.has_children():
                raise exceptions.DirectoryIsEmptyError(tree)
            commands.validate_tree(self.config, tree)
        total, dirs, files, symlinks = statistic.total_statistic(tree)
        audio_sup, audio_unsup, audio_del = statistic.audio_statistic(tree)
        image_sup, image_unsup, image_del = statistic.image_statistic(tree)
        self.view.show_stat('Find:', directories=dirs, files=files,
                            symlinks=symlinks)
        self.view.show_stat(' ' * 5, audio=audio_sup,
                            unsupported=audio_unsup, trash=audio_del)
        self.view.show_stat(' ' * 5, supported=image_sup,
                            unsupported=image_unsup, trash=image_del)
        # Apply user tags and save modified tags
        with self.view.show_wait('Save tags', 'Done!'):
            if self.tags:
                commands.apply_audio_tags(self.config, tree, self.tags)
            commands.save_audio_tags(self.config, tree)
        # Exit
        self.stop()

    def stop(self):
        sys.stdout.flush()

    config = property(get_config, set_config, doc='Application settings.')
    tags = property(get_tags, set_tags, doc='User defined audio tags.')
    view = property(get_view, doc='Compont responsible for displaying info.')


class View:
    """Methods for writing data to STDOUT."""

    @contextlib.contextmanager
    def show_wait(self, msg, end_msg=None, rate=1, size=5):
        """Displays dotted progress bar for a task in progress.

        Args:
            msg (str): Short description of executing task.
            end_msg (str): Message to indicate the end of execution.
            rate (:obj:`int`, optional): Refrash rate, in seconds.
            size (:obj:`int`, optional): Max length of progress bar.

        Yields:
            Thread that updates dotted progress bar.
        """

        def dots(msg, size, rate, event):
            tik = 0
            while not event.is_set():
                dotcount = tik % size + 1
                tik += 1
                sys.stdout.write('{msg}{dot: <{len}}\r'.format(
                    msg=msg, dot='.'*dotcount, len=size))
                time.sleep(rate)
            sys.stdout.write(
                '{space: <{len}}\r'.format(space=' ', len=len(msg)+size))

        event = threading.Event()
        thread = threading.Thread(target=dots, args=(msg, size, rate, event))
        try:
            thread.start()
            yield thread
        finally:
            event.set()
            thread.join()
            if end_msg:
                self.show_line(end_msg)

    def show_char(self, *chars):
        """Writes sequence of strings to STDOUT without adding EOL."""
        for char in chars:
            sys.stdout.write(str(char))
        sys.stdout.flush()

    def show_line(self, *lines):
        """
        Writes sequence of strings to STDOUT appending each string with EOL.
        """
        for line in lines:
            sys.stdout.write(str(line))
            sys.stdout.write(os.linesep)
        sys.stdout.flush()

    def show_eol(self):
        """Writes EOL character sequence to STDOUT."""
        sys.stdout.write(os.linesep)
        sys.stdout.flush()

    def show_stat(self, label, **kwargs):
        """Displays dictionaly as a labeled string."""
        txt = ', '.join('{0} {1}'.format(v, k) for k, v in kwargs.items() if v)
        if txt:
            self.show_char(label, ' ', txt)
            self.show_eol()


# vim: ts=4 sw=4 sts=4 et ai
