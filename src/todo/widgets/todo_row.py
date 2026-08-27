# SPDX-License-Identifier: GPL-3.0-or-later
"""List row widget for a single todo item."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GObject, Gtk, Pango

from todo.store import TodoItem


class TodoRow(Gtk.ListBoxRow):
    __gsignals__ = {
        "toggle": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "delete": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "edit": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, item: TodoItem) -> None:
        super().__init__()
        self.item = item
        self.set_activatable(False)

        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            margin_top=8,
            margin_bottom=8,
            margin_start=10,
            margin_end=8,
        )

        self.check = Gtk.CheckButton(active=item.completed)
        self.check.set_tooltip_text("Mark complete")
        self.check.connect("toggled", self._on_toggled)
        box.append(self.check)

        self.title = Gtk.Label(
            label=item.title,
            xalign=0,
            hexpand=True,
            wrap=True,
            ellipsize=Pango.EllipsizeMode.END,
        )
        self.title.add_css_class("todo-row-title")
        if item.completed:
            self.title.add_css_class("completed")
        self.title.set_selectable(False)
        box.append(self.title)

        self.edit_entry = Gtk.Entry(hexpand=True, visible=False)
        self.edit_entry.set_text(item.title)
        self.edit_entry.connect("activate", self._on_edit_activate)
        self.edit_entry.connect("notify::has-focus", self._on_edit_focus)
        box.append(self.edit_entry)

        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Edit")
        edit_btn.connect("clicked", self._on_edit_clicked)
        box.append(edit_btn)

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.set_tooltip_text("Delete")
        delete_btn.connect("clicked", lambda *_: self.emit("delete"))
        box.append(delete_btn)

        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self._on_title_pressed)
        self.title.add_controller(gesture)

        self.set_child(box)

    def _on_toggled(self, *_args) -> None:
        self.emit("toggle")

    def _on_edit_clicked(self, *_args) -> None:
        self._begin_edit()

    def _on_title_pressed(self, gesture, n_press, _x, _y) -> None:
        if n_press == 2:
            self._begin_edit()

    def _begin_edit(self) -> None:
        self.title.set_visible(False)
        self.edit_entry.set_text(self.item.title)
        self.edit_entry.set_visible(True)
        self.edit_entry.grab_focus()
        self.edit_entry.select_region(0, -1)

    def _on_edit_activate(self, *_args) -> None:
        self._commit_edit()

    def _on_edit_focus(self, entry: Gtk.Entry, _pspec) -> None:
        if self.edit_entry.get_visible() and not entry.has_focus():
            self._commit_edit()

    def _commit_edit(self) -> None:
        if not self.edit_entry.get_visible():
            return
        text = self.edit_entry.get_text().strip()
        self.edit_entry.set_visible(False)
        self.title.set_visible(True)
        if text and text != self.item.title:
            self.emit("edit", text)
