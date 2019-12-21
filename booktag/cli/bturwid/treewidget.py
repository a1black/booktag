"""Widgets for displaying a tree structure.

Tree widgets provided by *urwid* have strong coupling of data structure
implementation and user interface components. That makes it very hard to
implement architecture where a tree data structure is a shared resource
between background services, which operate on their own implementation of
a tree, and graphic interface, which must reflect changes made to shared data.

This module solves this propblem by implementing *urwid.ListWalker* that
maintains :class:`weakref.WeakKeyDictionary` mapping node instances to theirs
display widgets. This approach won't work if tree is a factory that yields
nodes as new objects.

Problems:
    * Tree objects must be cachable.
    * Hash collision would crush application if associated widget has
    dead reference to a node object.

Names of display attributes:
    node_row              - Whole  row  occupaied  by  node.
    node_row_focus        - *node_row* when in focus.
    expand_icon           - An icon of expand/collapse state.
    expand_icon_focus     - *expand_icon* when in focus.
    highlighted_row       - Row selected by user.
    highlighted_row_focus - *highlight_row* when in focus.
"""
import weakref

import urwid

from booktag.cli import command_map
from booktag.utils import behavioral


class TreeWidget(urwid.WidgetWrap):
    """A widget representing node in a rooted tree.

    Args:
        node: Weak reference to displayed node.

    Attributes:
        indent_cols (int): Number of screen columns per node's depth.
        expanded_icon: Collapse brance icon.
        unexpanded_icon: Expand branch icon.
    """
    indent_cols = 3
    expand_icon = urwid.AttrMap(urwid.SelectableIcon('+'),
                                'expand_icon', 'expand_icon_focus')
    collapse_icon = urwid.AttrMap(urwid.SelectableIcon('-'),
                                  'expand_icon', 'expand_icon_focus')

    def __init__(self, node):
        super().__init__(None)
        self._node = node
        self._flagged = False
        self._expanded = node.has_children()
        self._expand_widget = self._node_widget = None
        self.build_row_widget()

    def highlightable(self):
        return True

    def selectable(self):
        """Makes widget selectable."""
        return True

    def sizing(self):
        """Returns *flow* sizing mod."""
        return frozenset([urwid.FLOW])

    def get_node(self):
        return self._node

    def get_indent(self):
        """Returns indent size to indicate node's depth."""
        return self.indent_cols * self.get_node().get_depth()

    def get_flagged(self):
        """Returns True if node is selected by user."""
        return self._flagged

    def set_flagged(self, state):
        """Changes selection state."""
        oldvalue = self._flagged
        self._flagged = bool(state)
        if self._flagged != oldvalue:
            self.update_flagged()

    def toggle_flagged(self):
        """Inverts selection state."""
        self.set_flagged(not self.get_flagged())

    def get_expanded(self):
        """Returns True if child nodes of the branch is displayed."""
        return self._expanded

    def set_expanded(self, state):
        """Changes display state."""
        oldstate = self._expanded
        self._expanded = bool(state)
        if self._expanded != oldstate:
            self.update_expanded()

    def toggle_expanded(self):
        """Inverts display state."""
        self.set_expanded(not self.get_expanded())

    def update_flagged(self):
        """Updates visual selection of the row."""
        if self._flagged:
            self._w.set_attr_map({None: 'highlighted_row'})
            self._w.set_focus_map({None: 'highlighted_row_focus'})
        else:
            self._w.set_attr_map({None: 'node_row'})
            self._w.set_focus_map({None: 'node_row_focus'})

    def update_expanded(self):
        """Updates widget that indicates node's fold state."""
        if self._expand_widget:
            icon_widget = (self.collapse_icon
                           if self.get_expanded() else self.expand_icon)
            self._expand_widget.original_widget = icon_widget

    def update_value(self):
        """Updates node's displayed value."""
        if self._node_widget:
            self._node_widget.set_text(self.get_node().get_value())

    def rebuild(self):
        """Destroys wrapped widget and creates a new one."""
        self.build_row_widget()

    def build_row_widget(self):
        """Creates wrapped widget."""
        self._node_widget = self.get_node_widget()
        if self.get_node().has_children():
            self._expand_widget = urwid.WidgetPlaceholder(None)
            self.update_expanded()
            layout = [(1, self._expand_widget), self._node_widget]
            widget = urwid.Columns(layout, dividechars=1)
        else:
            self._expand_widget = None
            widget = self._node_widget
        widget = urwid.Padding(widget, width=urwid.RELATIVE_100,
                               left=self.get_indent())
        self._w = urwid.AttrMap(widget, None)
        self.update_flagged()

    def get_node_widget(self):
        """Returns widget that displayes node value."""
        return urwid.Text(self.get_node().get_value(), wrap='ellipsis')

    def keypress(self, size, key):
        cmd = urwid.command_map[key]
        if cmd == urwid.ACTIVATE and self.highlightable():
            self.toggle_flagged()  # Toggle visual selection
        elif cmd == command_map.SCALE_DOWN or cmd == urwid.CURSOR_LEFT:
            if self.get_node().has_children() and self.get_expanded():
                self.set_expanded(False)  # Hide list of child nodes
            else:
                return key  # Leaf node or list of child nodes is hidden
        elif cmd == command_map.SCALE_UP or cmd == urwid.CURSOR_RIGHT:
            if self.get_node().has_children():
                self.set_expanded(True)  # Show list of child nodes
            else:
                return key  # Node is a leaf, forward to a tree widget
        else:
            return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse press' and button == 1:
            if row == 0 and col == self.get_indent():
                self.toggle_expanded()
                return True
        return False

    flagged = property(get_flagged, set_flagged, doc="True if highlighted.")
    expanded = property(get_expanded, set_expanded,
                        doc="True if list of child nodes is shown.")


class TreeWalker(urwid.ListWalker, behavioral.Observer):
    """ListWalker-compatible class for displaying tree structure.

    Args:
        focus_node: tree node with the initail focus.
    """

    def __init__(self, focus_node):
        self._widget_cache = weakref.WeakKeyDictionary()
        self.focus = focus_node

    def _produce_widget(self, tree_node):
        """Returns new widget for a node object."""
        self._subscribe_to_observable(tree_node)
        widget = TreeWidget(weakref.proxy(tree_node))
        self._widget_cache[tree_node] = widget
        return widget

    def _next_widget(self, tree_node, godeep=True):
        """Returns next visible node after `tree_node`."""
        if tree_node is None:
            return None
        elif not godeep:
            next_sibling = tree_node.next_sibling()
            if next_sibling is not None:
                return next_sibling
            return self._next_widget(tree_node.get_parent(), False)
        elif tree_node.has_children() and self.get_widget(tree_node).expanded:
            return tree_node[0]
        return self._next_widget(tree_node, False)

    def _prev_widget(self, tree_node, godeep=False):
        """Returns next visible node above `tree_node`."""
        if tree_node is None:
            return None
        elif godeep:
            if (tree_node.has_children()
                    and self.get_widget(tree_node).expanded):
                return self._prev_widget(tree_node[-1], True)
            return tree_node
        else:
            prev_sibling = tree_node.prev_sibling()
            if prev_sibling is None:
                return tree_node.get_parent()
            else:
                return self._prev_widget(prev_sibling, True)

    def listen_observable(self, subject, event, *args, **kwargs):
        """Updates widgets of modified node objects."""
        widget = self.get_widget(subject)
        if event == 'update_value' and widget is not None:
            widget.update_value()
        elif event == 'add_child':
            child_widget = self.get_widget(args[0]) if args else None
            if widget is not None and subject.get_degree() == 1:
                widget.rebuild()
            if child_widget is not None:
                child_widget.rebuild()
        elif event == 'remove_child':
            child_widget = self.get_widget(args[0]) if args else None
            if widget is not None and subject.get_degree() == 0:
                widget.rebuild()
            if child_widget is not None:
                child_widget.rebuild()
        self._modified()

    def get_focus(self):
        """Returns a `(focus widget, focus position)` tuple."""
        return self.widget, self.focus

    def set_focus(self, focus_node):
        """Updates references to a node in focus."""
        self.focus = focus_node
        self._modified()

    def get_widget(self, tree_node=None):
        """Returns display widget for `tree_node`."""
        if tree_node is None:
            tree_node = self.focus
        try:
            widget = self._widget_cache[tree_node]
        except KeyError:
            widget = self._produce_widget(tree_node)
        return widget

    def get_next(self, tree_node):
        """Returns node displayed below the `tree_node`."""
        next_node = self._next_widget(tree_node)
        if next_node is None:
            return None, None
        else:
            return self.get_widget(next_node), next_node

    def get_prev(self, tree_node):
        """Returns node displayed above the `tree_node`."""
        prev_node = self._prev_widget(tree_node)
        if prev_node is None:
            return None, None
        else:
            return self.get_widget(prev_node), prev_node

    def home(self):
        """Returns the root node."""
        return self.focus.get_root()

    def end(self):
        """Returns the last visible node."""
        return self._prev_widget(self.focus.get_root(), True)

    def get_selected(self):
        """Returns list of selected nodes."""
        selected = []
        for node, widget in self._widget_cache.items():
            if widget.flagged:
                selected.append(node)
        return selected

    def clear_selected(self):
        """Removes visual selection."""
        for widget in self._widget_cache.values():
            widget.set_flagged(False)
        self._modified()

    widget = property(get_widget, doc="Display widget for the node in focus.")


class TreeListBox(urwid.ListBox):
    """ListBox for displaying tree structure.

    Args:
        body(:class:`TreeWalker`): Object for navigation a rooted tree.
    """

    def __init__(self, body):
        if not isinstance(body, TreeWalker):
            raise TypeError('{0}() expected TreeWalker, got {1}'.format(
                type(self).__name__, type(body).__name__))
        super().__init__(body)

    def keypress(self, size, key):
        key = super().keypress(size, key)
        return self.unhandled_input(size, key)

    def unhandled_input(self, size, key):
        cmd = urwid.command_map[key]
        if cmd == urwid.CURSOR_LEFT:
            self._keypress_move_left(size)
        elif cmd == command_map.SCALE_DOWN:
            self._keypress_move_left(size)
            self.body.widget.set_expanded(False)
        elif cmd == command_map.STOP:
            self.body.clear_selected()
        else:
            return key

    def _keypress_move_left(self, size):
        """Move focus to parent node."""
        parent = self.body.focus.get_parent()
        if parent is not None:
            middle, top, bottom = self.calculate_visible(size)
            row_offset = middle[0]
            fill_above = top[1]
            for widget, pos, rows in fill_above:
                row_offset -= rows
                if pos == parent:
                    self.change_focus(size, pos, row_offset)
                    break
            else:
                self.change_focus(size, pos.get_parent())

    def _keypress_max_left(self, size):
        """Moves focus to the root."""
        self.change_focus(size, self.body.home())

    def _keypress_max_right(self, size):
        """Moves to the last visible node."""
        self.change_focus(size, self.body.end(), size[1] - 1)

# vim: ts=4 sw=4 sts=4 et ai
