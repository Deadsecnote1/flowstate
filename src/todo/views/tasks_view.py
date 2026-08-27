# SPDX-License-Identifier: GPL-3.0-or-later
"""Tasks list page: entry, filters, list, status."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GObject, Gtk

from todo.store import FilterMode, TodoStore
from todo.widgets import TodoRow

ToastFn = Callable[[str], None]
FilterMap = {"all": 0, "active": 1, "completed": 2}
FilterByIndex: list[FilterMode] = ["all", "active", "completed"]


class TasksPage(Gtk.Box):
    """Independent Tasks feature page."""

    __gsignals__ = {
        "request-toast": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, store: TodoStore, startup_filter: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.store = store
        self._filter: FilterMode = FilterByIndex[startup_filter] if 0 <= startup_filter <= 2 else "all"
        self._query = ""
        self._confirm_delete = False
        self._settings: Gio.Settings | None = None

        self._build_ui()
        self._apply_startup_filter()
        self.store.subscribe(self.refresh)
        self.refresh()

    def set_settings(self, settings: Gio.Settings | None) -> None:
        self._settings = settings
        if settings is not None:
            self._confirm_delete = settings.get_boolean("confirm-delete")
            settings.connect("changed::confirm-delete", self._on_confirm_changed)
            settings.connect("changed::startup-filter", self._on_startup_filter_changed)

    def _on_confirm_changed(self, settings: Gio.Settings, _key: str) -> None:
        self._confirm_delete = settings.get_boolean("confirm-delete")

    def _on_startup_filter_changed(self, settings: Gio.Settings, _key: str) -> None:
        # Only affects next launch; keep current session unless user asks otherwise.
        pass

    def _apply_startup_filter(self) -> None:
        mode = self._filter
        mapping = {
            "all": self.filter_all,
            "active": self.filter_active,
            "completed": self.filter_completed,
        }
        mapping[mode].set_active(True)

    def _build_ui(self) -> None:
        self.entry = Gtk.Entry(
            placeholder_text="What needs doing?",
            hexpand=True,
        )
        self.entry.add_css_class("todo-entry")
        self.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "list-add-symbolic"
        )
        self.entry.connect("activate", self.on_add)
        self.entry.connect("icon-press", lambda *_: self.on_add())
        self.append(self.entry)

        filter_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            halign=Gtk.Align.CENTER,
        )
        filter_box.add_css_class("filter-bar")
        self.filter_all = Gtk.ToggleButton(label="All", active=True)
        self.filter_active = Gtk.ToggleButton(label="Active")
        self.filter_completed = Gtk.ToggleButton(label="Done")
        self.filter_active.set_group(self.filter_all)
        self.filter_completed.set_group(self.filter_all)
        for btn, mode in (
            (self.filter_all, "all"),
            (self.filter_active, "active"),
            (self.filter_completed, "completed"),
        ):
            btn.add_css_class("flat")
            btn.connect("toggled", self.on_filter_toggled, mode)
            filter_box.append(btn)
        self.append(filter_box)

        self.content_stack = Gtk.Stack(vexpand=True)
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(12)
        self.list_box.set_margin_end(12)
        self.list_box.set_margin_bottom(12)
        scrolled.set_child(self.list_box)
        self.content_stack.add_named(scrolled, "list")

        self.empty_page = Adw.StatusPage(
            icon_name="checkbox-checked-symbolic",
            title="Nothing here yet",
            description="Add a task above to get started.",
        )
        self.content_stack.add_named(self.empty_page, "empty")
        self.append(self.content_stack)

        self.status_label = Gtk.Label(xalign=0)
        self.status_label.add_css_class("status-bar")
        self.status_label.add_css_class("dim-label")
        self.append(self.status_label)

    def focus_entry(self) -> None:
        self.entry.grab_focus()

    def set_search_query(self, query: str) -> None:
        self._query = query
        self.refresh()

    def on_add(self, *_args) -> None:
        item = self.store.add(self.entry.get_text())
        if item:
            self.entry.set_text("")
            self.emit("request-toast", "Task added")
            self.entry.grab_focus()
            if self._settings is not None:
                self._settings.set_int("startup-filter", FilterMap.get(self._filter, 0))

    def on_filter_toggled(self, button: Gtk.ToggleButton, mode: FilterMode) -> None:
        if button.get_active():
            self._filter = mode
            if self._settings is not None:
                self._settings.set_int("startup-filter", FilterMap[mode])
            self.refresh()

    def clear_completed(self) -> None:
        removed = self.store.clear_completed()
        if removed:
            self.emit("request-toast", f"Cleared {removed} completed")

    def archive_completed(self) -> None:
        archived = self.store.archive_completed()
        if archived:
            self.emit("request-toast", f"Archived {archived} completed")
        else:
            self.emit("request-toast", "No completed tasks to archive")

    def refresh(self) -> None:
        while (child := self.list_box.get_first_child()) is not None:
            self.list_box.remove(child)

        items = self.store.filtered(self._filter, self._query)
        for item in items:
            row = TodoRow(item)
            row.connect("toggle", self._on_row_toggle)
            row.connect("delete", self._on_row_delete)
            row.connect("edit", self._on_row_edit)
            self.list_box.append(row)

        total, active, completed = self.store.counts()
        if total == 0:
            self.content_stack.set_visible_child_name("empty")
            self.empty_page.set_title("Nothing here yet")
            self.empty_page.set_description("Add a task above to get started.")
            self.status_label.set_text("No tasks yet")
        elif not items:
            self.content_stack.set_visible_child_name("empty")
            self.empty_page.set_title("No matching tasks")
            self.empty_page.set_description("Try another filter or search.")
            self.status_label.set_text(f"{active} active · {completed} done")
        else:
            self.content_stack.set_visible_child_name("list")
            noun = "task" if active == 1 else "tasks"
            self.status_label.set_text(f"{active} {noun} left · {completed} done")

    def _on_row_toggle(self, row: TodoRow) -> None:
        self.store.toggle(row.item.id)

    def _on_row_delete(self, row: TodoRow) -> None:
        if self._confirm_delete:
            dialog = Adw.AlertDialog(
                heading="Delete task?",
                body=f"Delete “{row.item.title}”?",
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "Delete")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", self._on_delete_response, row.item.id)
            dialog.present(self.get_root())
            return
        self.store.remove(row.item.id)
        self.emit("request-toast", "Task deleted")

    def _on_delete_response(self, dialog: Adw.AlertDialog, response: str, item_id: str) -> None:
        if response == "delete":
            self.store.remove(item_id)
            self.emit("request-toast", "Task deleted")

    def _on_row_edit(self, row: TodoRow, title: str) -> None:
        self.store.update_title(row.item.id, title)
