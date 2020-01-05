import enum

from booktag.utils import collections


class _StrValue:
    """Converts value to a string.

    If value is an iterable, it is concatenated with the `sep` string.

    Args:
        sep (str): The delimiter string.
    """

    def __init__(self, sep):
        self._sep = str(sep) if sep else ''

    def __call__(self, value):
        try:
            if isinstance(value, (bytes, bytearray)):
                return bytes(value).decode()
            elif isinstance(value, str):
                return value
            else:
                return self._sep.join(map(str, value))
        except UnicodeError:
            raise ValueError('byte string without decoding')
        except TypeError:
            return str(value)


class _ListValue:
    """Converts value to a list of same type values.

    Args:
        basetype (callable): Type of values in the list.
    """

    def __init__(self, basetype):
        self._basetype = basetype

    def __call__(self, value):
        try:
            if isinstance(value, (str, bytes)):
                raise TypeError
            iterator = iter(value)
        except TypeError:
            iterator = iter([value])
        newvalue = []
        for index, item in enumerate(iterator):
            try:
                newvalue.append(self._basetype(item))
            except (TypeError, ValueError) as err:
                raise err.__class__(
                    'sequence item {0}: {1}'.format(index, err)) from err
        return newvalue


class Names(str, enum.Enum):
    """Supported audio tags."""
    ALBUM = 'album'
    ALBUMARTIST = 'albumartist'
    ALBUMSORT = 'albumsort'
    ARTIST = 'artist'
    COMMENT = 'comment'
    COMPOSER = 'composer'
    DATE = 'date'
    DISCNUM = 'discnumber'
    DISCTOTAL = 'disctotal'
    GENRE = 'genre'
    GROUPING = 'grouping'
    LABEL = 'label'
    ORIGINALDATE = 'originaldate'
    TITLE = 'title'
    TRACKNUM = 'tracknumber'
    TRACKTOTAL = 'tracktotal'


_filters = {
    Names.ALBUM: _StrValue(sep=' '),
    Names.ALBUMARTIST: _ListValue(str),
    Names.ALBUMSORT: int,
    Names.ARTIST: _ListValue(str),
    Names.COMMENT: _StrValue(sep=' '),
    Names.COMPOSER: _ListValue(str),
    Names.DATE: int,
    Names.DISCNUM: int,
    Names.DISCTOTAL: int,
    Names.GENRE: _ListValue(str),
    Names.GROUPING: _StrValue(sep=' '),
    Names.LABEL: _StrValue(sep=' '),
    Names.ORIGINALDATE: int,
    Names.TITLE: _StrValue(sep=' '),
    Names.TRACKNUM: int,
    Names.TRACKTOTAL: int
}


class Tags(collections.UserDict):
    """Audio file tag container."""

    def __init__(self, data=None, **kwargs):
        super().__init__()
        self.__dict__.update(_filters=_filters)
        if data is not None:
            self.update(data)
        self.update(kwargs)

    def __copy__(self):
        return self.__class__(self._data)

    def __setitem__(self, key, value):
        """Applies filter object to the value before saving it."""
        try:
            if value is None:
                del self[key]
            elif key in self._filters:
                self._data[key] = self._filters[key](value)
            else:
                self._data[key] = value
        except KeyError:
            # We do not need None is dictionary.
            pass
        except (TypeError, ValueError) as e:
            raise e.__class__('meta item {0!r}: {1}'.format(key, e)) from e
