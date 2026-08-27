# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from todo.window import TodoWindow  # noqa: E402

APP_ID = "io.github.thanushiyan.Todo"


class TodoApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about)
        self.create_action("preferences", self.on_preferences)

    def do_activate(self) -> None:
        win = self.props.active_window
        if not win:
            win = TodoWindow(application=self)
            if getattr(win.store, "load_error", None):
                win.show_toast(
                    "Task list file was unreadable; started with an empty list",
                    timeout=5,
                )
            if getattr(win.planner_store, "load_error", None):
                win.show_toast(
                    "Planner file was unreadable; started empty",
                    timeout=5,
                )
        win.present()

    def do_shutdown(self) -> None:
        # Belt-and-suspenders: release any idle/suspend inhibit before exit.
        for window in list(self.get_windows()):
            if isinstance(window, TodoWindow):
                window.prepare_for_shutdown()
        Adw.Application.do_shutdown(self)

    def on_about(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name="Todo",
            application_icon=APP_ID,
            developer_name="Thanushiyan",
            version="1.0.0",
            developers=["Thanushiyan"],
            copyright="© 2026 Thanushiyan",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/Deadsecnote1/flowstate",
            issue_url="https://github.com/Deadsecnote1/flowstate/issues",
            comments=(
                "Task list, daily planner, and clock (timer / stopwatch) "
                "for GNOME and Debian desktops. Closing the app stops timers."
            ),
        )
        about.present(self.props.active_window)

    def on_preferences(self, *_args) -> None:
        from todo.preferences import PreferencesDialog

        dialog = PreferencesDialog()
        dialog.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(argv: list[str] | None = None) -> int:
    app = TodoApplication()
    return app.run(argv or sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
