import enum


class AudioType(str, enum.Enum):
    """Enumeration of supported audio file formats."""
    FLAC = 'FLAC'
    MP3 = 'MP3'
    MP4 = 'MP4'
    OGG = 'OGG'


class ImageType(str, enum.Enum):
    """Enumeration of supported image file formats."""
    JPEG = 'JPEG'
    PNG = 'PNG'


class TagName(str, enum.Enum):
    """Enumeration of metadata tags supported by the application."""

    ALBUM = 'album'
    ALBUMARTIST = 'albumartist'
    ALBUMSORT = 'albumsort'
    ARTIST = 'artist'
    COMMENT = 'comment'
    COMPOSER = 'composer'
    COVER = 'cover'
    DATE = 'date'
    DISCNUM = 'discnum'
    DISCTOTAL = 'disctotal'
    GENRE = 'genre'
    GROUPING = 'grouping'
    LABEL = 'label'
    ORIGINALDATE = 'originaldate'
    TITLE = 'title'
    TRACKNUM = 'tracknum'
    TRACKTOTAL = 'tracktotal'


class PictureType(enum.IntEnum):
    """Enumeration of embedded picture types defined by the ID3 standard."""

    OTHER = enum.auto()               # Other
    FILE_ICON = enum.auto()           # 32x32 pixels 'file icon' (PNG only)
    OTHER_FILE_ICON = enum.auto()     # Other file icon
    COVER_FRONT = enum.auto()         # Cover (front)
    COVER_BACK = enum.auto()          # Cover (back)
    LEAFLET_PAGE = enum.auto()        # Leaflet page
    MEDIA = enum.auto()               # Media (e.g. label side of CD)
    LEAD_ARTIST = enum.auto()         # Lead artist/lead performer/soloist
    ARTIST = enum.auto()              # Artist/performer
    CONDUCTOR = enum.auto()           # Conductor
    BAND = enum.auto()                # Band/Orchestra
    COMPOSER = enum.auto()            # Composer
    LYRICIST = enum.auto()            # Lyricist/text writer
    RECORDING_LOCATION = enum.auto()  # Recording Location
    DURING_RECORDING = enum.auto()    # During recording
    DURING_PERFORMANCE = enum.auto()  # During performance
    SCREEN_CAPTURE = enum.auto()      # Movie/video screen capture
    FISH = enum.auto()                # A bright coloured fish
    ILLUSTRATION = enum.auto()        # Illustration
    BAND_LOGOTYPE = enum.auto()       # Band/artist logotype
    PUBLISHER_LOGOTYPE = enum.auto()  # Publisher/Studio logotype
