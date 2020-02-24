import collections
import json
import os

import ruamel.yaml as yaml

from booktag import streams


class InvalidConfigurationError(Exception):
    """Raised when reading invalid or corrupted configuration file."""


class SettingContainer(collections.UserDict):
    """Class provides access to nested dictionaries using composite key.

    Composite key is a sequence of keys separeted by a dot.
    """

    def __init__(self):
        self.data = {}

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __getitem__(self, key):
        try:
            dict_, node = self._descend(key)
            return dict_[node]
        except (KeyError, TypeError):
            raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            dict_, node = self._descend(key, fillin=True)
            if not isinstance(value, type(self)) and hasattr(value, 'keys'):
                value = self.__class__(value)
            dict_[node] = value
        except (KeyError, TypeError):
            raise KeyError(key)

    def __delitem__(self, key):
        try:
            dict_, node = self._descend(key)
            del dict_[node]
        except (KeyError, ValueError):
            raise KeyError(key)

    def _descend(self, key, fillin=False):
        path = list(filter(None, key.split('.')))
        if not path:
            raise KeyError(key)
        end = path.pop()
        root = self.data
        for node in path:
            try:
                root = root[node]
            except TypeError:
                raise KeyError(key)
            except KeyError:
                if fillin:
                    root[node] = self.__class__()
                    root = root[node]
                else:
                    raise
        return root, end

    def clear(self):
        self.data.clear()


class Settings:

    def __init__(self):
        self.__dict__.update(_settings=SettingContainer())
        self.clear()

    def __contains__(self, key):
        return key in self._settings

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(
                type(self).__name__, name))

    def __setattr__(self, name, value):
        self._settings.update(name=value)

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(
                type(self).__name__, name))

    def __getitem__(self, key):
        return self._settings[key]

    def __setitem__(self, key, value):
        self._settings[key] = value

    def __delitem__(self, key):
        del self._settings[key]

    def _load_defaults(self):
        self._settings.data['album_metadata'] = streams.Metadata()
        self['metadata.tags.drop'] = set(['comment', 'legal', 'rating', 'url'])
        self['metadata.cover.minsize'] = 500
        self['metadata.cover.maxsize'] = 1000
        self['metadata.cover.filesize'] = 250 * 1024

    def clear(self):
        self._settings.clear()
        self._load_defaults()

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def from_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == 'json':
            self.from_json(path)
        else:
            self.from_yaml(path)

    def from_json(self, path):
        with open(path, 'r') as stream:
            try:
                self._settings.update(json.load(stream))
            except json.JSONDecodeError as error:
                raise InvalidConfigurationError(
                    'Invalid JSON configuraton file') from error

    def from_yaml(self, path):
        with open(path, 'r') as stream:
            try:
                self._settings.update(yaml.safe_load(stream))
            except yaml.YAMLError as error:
                raise InvalidConfigurationError(
                    'Invalid YAML configuration file') from error


settings = Settings()
