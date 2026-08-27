# SPDX-License-Identifier: GPL-3.0-or-later
"""Preferences dialog."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from todo.settings import APP_ID, get_settings


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self) -> None:
        super().__init__()
        self.set_title("Preferences")

        settings = get_settings()

        page = Adw.PreferencesPage(
            title="General", icon_name="preferences-system-symbolic"
        )
        group = Adw.PreferencesGroup(title="Behavior")

        confirm_row = Adw.SwitchRow(
            title="Confirm before deleting",
            subtitle="Ask for confirmation when removing a task",
        )
        startup_row = Adw.ComboRow(title="Default task filter")
        startup_row.set_model(
            Gtk.StringList.new(["All tasks", "Active only", "Completed only"])
        )

        if settings:
            from gi.repository import Gio

            settings.bind(
                "confirm-delete",
                confirm_row,
                "active",
                Gio.SettingsBindFlags.DEFAULT,
            )
            settings.bind(
                "startup-filter",
                startup_row,
                "selected",
                Gio.SettingsBindFlags.DEFAULT,
            )
        else:
            confirm_row.set_active(False)
            confirm_row.set_sensitive(False)
            startup_row.set_selected(0)
            startup_row.set_sensitive(False)

        group.add(confirm_row)
        group.add(startup_row)
        page.add(group)
        self.add(page)
