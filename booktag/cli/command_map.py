import urwid

REDRAW_SCREEN = urwid.REDRAW_SCREEN
CLOSE = 'close'
SCALE_UP = 'scale up'
SCALE_DOWN = 'scale down'
CURSOR_UP = urwid.CURSOR_UP
CURSOR_DOWN = urwid.CURSOR_DOWN
CURSOR_LEFT = urwid.CURSOR_LEFT
CURSOR_RIGHT = urwid.CURSOR_RIGHT
CURSOR_PAGE_UP = urwid.CURSOR_PAGE_UP
CURSOR_PAGE_DOWN = urwid.CURSOR_PAGE_DOWN
CURSOR_MAX_LEFT = urwid.CURSOR_MAX_LEFT
CURSOR_MAX_RIGHT = urwid.CURSOR_MAX_RIGHT
NEXT_ITEM = 'next selectable',
PREV_ITEM = 'prev selectable',
ACTIVATE = urwid.ACTIVATE
CONFIRM = 'confirm'
STOP = 'stop'
BACKSPACE = 'backspace'


class CommandMap:
    """Default mapping for looking up commands from keystrokes."""

    def __init__(self, *args, **kwargs):
        self._mapping = {}
        self._load_defaults()

    def __contains__(self, key):
        return key in self._mapping

    def __getitem__(self, key):
        """Returns command bound to a given keystroke `key`or None."""
        return self._mapping.get(key, None)

    def __setitem__(self, key, value):
        """Registers keyboard shortcut."""
        self._mapping[key] = value

    def __delitem__(self, key):
        try:
            del self._mapping[key]
        except KeyError:
            pass

    def clear_command(self, command):
        """Removes key bindings for a given command."""
        keys = [k for k, v in self._mapping.items() if v == command]
        for key in keys:
            del self[key]

    def restore_default(self):
        self._mapping = {}
        self._load_defaults()

    def update(self, values):
        self._mapping.update(values)

    def _load_defaults(self):
        self.update({
            'up':         CURSOR_UP,
            'down':       CURSOR_DOWN,
            'left':       CURSOR_LEFT,
            'right':      CURSOR_RIGHT,
            'page up':    CURSOR_PAGE_UP,
            'page down':  CURSOR_PAGE_DOWN,
            'home':       CURSOR_MAX_LEFT,
            'end':        CURSOR_MAX_RIGHT,
            'tab':        NEXT_ITEM,
            'shift tab':  PREV_ITEM,
            ' ':          ACTIVATE,
            'enter':      CONFIRM,
            'esc':        STOP,
            'backspace':  BACKSPACE,
            '+':          SCALE_UP,
            '-':          SCALE_DOWN,
            'ctrl l':     REDRAW_SCREEN
        })


class VimMap(CommandMap):
    """Vim-like key mapping."""

    def _load_defaults(self):
        super()._load_defaults()
        self.update({
            'k':       CURSOR_UP,
            'ctrl y':  CURSOR_UP,
            'j':       CURSOR_DOWN,
            'ctrl e':  CURSOR_DOWN,
            'ctrl b':  CURSOR_PAGE_UP,
            'ctrl f':  CURSOR_PAGE_DOWN,
            'g':       CURSOR_MAX_LEFT,
            'G':       CURSOR_MAX_RIGHT,
            'ctrl n':  NEXT_ITEM,
            'ctrl p':  PREV_ITEM,
            'ctrl h':  BACKSPACE,
            'ctrl [':  STOP,
            'ctrl x':  CLOSE
        })


def default_mapping():
    urwid.command_map = CommandMap()


def vim_mapping():
    urwid.command_map = VimMap()


# vim: ts=4 sw=4 sts=4 et ai
