import os
import sys

from booktag import exceptions
from booktag.app import commands
from booktag.services import metafunc
from booktag.services import statistic


class App:
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
        self.view.silent = self.config.get('run_setting.quiet')
        encoding = self.config.get('read_setting.audio.encoding')
        path = self.config.get('run_setting.path')
        if not (path and (encoding or self.tags)):
            self.view.show_msg('There is nothing to do, terminate application')
            self.stop()
        # Load data
        self.view.show_msg('Load path ...')
        tree = commands.build_tree(self.config, path)
        total_afiles, supp_afiles, del_afiles = statistic.audio_statistic(tree)
        self.view.show_msg(
            'Find: {0} audio files, {1} supported, {2} for deletion'.format(
                *statistic.audio_statistic(tree)))

        # Validate data
        if metafunc.is_dir_node(tree) and not tree.has_children():
            raise exceptions.DirectoryIsEmptyError(tree)
        commands.validate_tree(self.config, tree)
        # Apply user tags
        if self.tags:
            commands.apply_audio_tags(self.config, tree, self.tags)
        # Save modified tags
        self.view.show_msg('Save tags...')
        commands.save_audio_tags(self.config, tree)
        # Exit
        self.view.show_msg('Done!')

    def stop(self):
        sys.exit()

    config = property(get_config, set_config, doc='Application settings.')
    tags = property(get_tags, set_tags, doc='User defined audio tags.')
    view = property(get_view, doc='Compont responsible for displaying info.')


class View:
    tabwidth = 2

    def __init__(self, silent=False):
        self.silent = silent

    def show_msg(self, *args, line=True, indent=0, chr=' '):
        if self.silent:
            return
        if indent:
            args = (chr * indent * self.tabwidth,) + args
        if line:
            print(*args, file=sys.stdout, sep=os.linesep)
        else:
            print(*args, file=sys.stdout, end=' ')

    def show_error(self, msg, blanks=0):
        if self.silent:
            return
        for _ in range(blanks):
            print('', file=sys.stderr)
        print('Error:', msg, file=sys.stderr)


# vim: ts=4 sw=4 sts=4 et ai
