import urwid

CLOSE = 'close'
SCALE_UP = 'scale up'
SCALE_DOWN = 'scale down'
NEXT_ITEM = 'next selectable',
PREV_ITEM = 'prev selectable',
CONFIRM = 'confirm'
STOP = 'stop'
BACKSPACE = 'backspace'


"""disct: Extension for default mapping defined by Urwid library."""
DEFAULT_KEY_MAP = {
    'tab':        NEXT_ITEM,
    'shift tab':  PREV_ITEM,
    'enter':      CONFIRM,
    'esc':        STOP,
    'backspace':  BACKSPACE,
    '+':          SCALE_UP,
    '-':          SCALE_DOWN
}

"""dict: Vim-like key mapping."""
VIM_KEY_MAP = {
    'k':       urwid.CURSOR_UP,
    'ctrl y':  urwid.CURSOR_UP,
    'j':       urwid.CURSOR_DOWN,
    'ctrl e':  urwid.CURSOR_DOWN,
    'ctrl b':  urwid.CURSOR_PAGE_UP,
    'ctrl f':  urwid.CURSOR_PAGE_DOWN,
    'g':       urwid.CURSOR_MAX_LEFT,
    'G':       urwid.CURSOR_MAX_RIGHT,
    'ctrl n':  NEXT_ITEM,
    'ctrl p':  PREV_ITEM,
    'ctrl h':  BACKSPACE,
    'ctrl [':  STOP,
    'ctrl x':  CLOSE
}


def restore_defaults():
    urwid.command_map.restore_defaults()
    for key, command in DEFAULT_KEY_MAP.items():
        urwid.command_map[key] = command


def vim_mapping():
    restore_defaults()
    for key, commamd in VIM_KEY_MAP.items():
        urwid.command_map[key] = commamd


vim_mapping()

# vim: ts=4 sw=4 sts=4 et ai
