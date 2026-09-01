# SPDX-License-Identifier: GPL-3.0-or-later
"""Preferences dialog."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk

from flowstate.settings import APP_ID, get_settings
from flowstate.sync.config import config_file_path, is_sync_configured
from flowstate.sync.engine import SyncEngine


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, sync_engine: SyncEngine | None = None) -> None:
        super().__init__()
        self.set_title("Preferences")
        self._sync = sync_engine

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

        self.add(self._build_sync_page())

    def _build_sync_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Sync", icon_name="cloud-symbolic")
        group = Adw.PreferencesGroup(
            title="Account",
            description="Sign in with Google to sync tasks and planner across devices.",
        )

        status = (
            self._sync.status_text
            if self._sync is not None
            else "Sync engine unavailable"
        )
        self._sync_status = Adw.ActionRow(title="Status", subtitle=status)
        group.add(self._sync_status)

        if self._sync:
            self._sync.set_status_listener(self._refresh_sync_status)

        config_row = Adw.ActionRow(
            title="Configuration file",
            subtitle=str(config_file_path()),
        )
        group.add(config_row)

        if not is_sync_configured():
            setup_row = Adw.ActionRow(
                title="Setup required",
                subtitle="Copy config/sync.env.example to the path above",
            )
            group.add(setup_row)
        elif self._sync and not self._sync.is_available():
            deps_row = Adw.ActionRow(
                title="Install sync support",
                subtitle="pip install --user -r requirements-sync.txt",
            )
            group.add(deps_row)
        elif self._sync is None:
            setup_row = Adw.ActionRow(
                title="Sync unavailable",
                subtitle="Restart the app after installing dependencies",
            )
            group.add(setup_row)

        actions = Adw.PreferencesGroup(title="Actions")
        sync_enabled = self._sync is not None

        sign_in_btn = Gtk.Button(label="Sign in with Google")
        sign_in_btn.add_css_class("suggested-action")
        sign_in_btn.set_sensitive(sync_enabled)
        sign_in_btn.connect("clicked", self._on_sign_in)
        sign_in_row = Adw.ActionRow(title="Sign in")
        sign_in_row.add_suffix(sign_in_btn)
        sign_in_row.set_activatable(False)
        actions.add(sign_in_row)

        sync_btn = Gtk.Button(label="Sync now")
        sync_btn.set_sensitive(sync_enabled)
        sync_btn.connect("clicked", self._on_sync_now)
        sync_row = Adw.ActionRow(title="Sync now")
        sync_row.add_suffix(sync_btn)
        sync_row.set_activatable(False)
        actions.add(sync_row)

        sign_out_btn = Gtk.Button(label="Sign out")
        sign_out_btn.set_sensitive(sync_enabled)
        sign_out_btn.connect("clicked", self._on_sign_out)
        sign_out_row = Adw.ActionRow(title="Sign out")
        sign_out_row.add_suffix(sign_out_btn)
        sign_out_row.set_activatable(False)
        actions.add(sign_out_row)

        page.add(group)
        page.add(actions)
        return page

    def _refresh_sync_status(self) -> None:
        if self._sync and hasattr(self, "_sync_status"):
            email = self._sync.session_email()
            subtitle = self._sync.status_text
            if email:
                subtitle = f"{email} — {subtitle}"
            self._sync_status.set_subtitle(subtitle)

    def _on_sign_in(self, *_args) -> None:
        if not self._sync:
            return
        self._sync_status.set_subtitle("Opening browser…")

        def done(message: str) -> None:
            self._refresh_sync_status()
            app_win = self.get_transient_for()
            if app_win is not None and hasattr(app_win, "show_toast"):
                app_win.show_toast(message, timeout=4)

        self._sync.sign_in_async(on_done=done)

    def _on_sync_now(self, *_args) -> None:
        if not self._sync:
            return
        self._sync.run_sync_async(on_done=lambda msg: self._refresh_sync_status())

    def _on_sign_out(self, *_args) -> None:
        if not self._sync:
            return
        self._sync.sign_out_user()
        self._refresh_sync_status()
