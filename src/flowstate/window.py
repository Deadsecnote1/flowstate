# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window — shell only (navigation, toasts, global actions)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from flowstate.settings import get_settings
from flowstate.store import PlannerStore, TodoStore
from flowstate.styles import APP_CSS
from flowstate.views import ClockPage, PlannerPage, TasksPage

APP_ID = "io.github.Deadsecnote1.Flowstate"


class FlowstateWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title("Flowstate")
        self.settings = get_settings()
        self._inhibit_cookie = 0

        width = 1100
        height = 720
        if self.settings is not None:
            width = self.settings.get_int("window-width") or width
            height = self.settings.get_int("window-height") or height
        self.set_default_size(width, height)
        if self.settings is not None and self.settings.get_boolean("window-maximized"):
            self.maximize()

        startup_filter = 0
        if self.settings is not None:
            startup_filter = self.settings.get_int("startup-filter")

        self.store = TodoStore(APP_ID)
        self.planner_store = PlannerStore(APP_ID)
        self.tasks_page = TasksPage(self.store, startup_filter=startup_filter)
        self.tasks_page.set_settings(self.settings)
        self.tasks_page.connect("request-toast", self._on_page_toast)

        self.planner_page = PlannerPage(self.planner_store)
        self.clock_page = ClockPage()
        self.clock_page.set_settings(self.settings)
        self.clock_page.set_timer_finished_callback(self._on_timer_finished)
        self.clock_page.set_timer_running_changed_callback(self._on_timer_running)

        self._build_ui()
        self._restore_last_view()
        self.create_action("add", self.on_add, ["<primary>n"])
        self.create_action("search", self.on_toggle_search, ["<primary>f"])
        self.create_action("clear-completed", self.on_clear_completed)
        self.create_action("archive-completed", self.on_archive_completed)
        self._load_css()
        self.tasks_page.focus_entry()
        self.connect("close-request", self._on_close)
        self.connect("notify::maximized", self._on_maximized_changed)

    def _load_css(self) -> None:
        css = Gtk.CssProvider()
        css.load_from_data(APP_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )

    def _build_ui(self) -> None:
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar)

        self.root_stack = Adw.ViewStack(vexpand=True)
        self.root_stack.add_titled_with_icon(
            self.tasks_page, "tasks", "Tasks", "view-list-symbolic"
        )
        self.root_stack.add_titled_with_icon(
            self.planner_page, "planner", "Planner", "x-office-calendar-symbolic"
        )
        self.root_stack.add_titled_with_icon(
            self.clock_page, "clock", "Clock", "preferences-system-time-symbolic"
        )

        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher(
            stack=self.root_stack,
            policy=Adw.ViewSwitcherPolicy.WIDE,
        )
        header.set_title_widget(switcher)

        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_button.set_menu_model(self._build_menu())
        header.pack_end(menu_button)

        self.search_btn = Gtk.ToggleButton(icon_name="system-search-symbolic")
        self.search_btn.set_tooltip_text("Search (Ctrl+F)")
        header.pack_end(self.search_btn)
        toolbar.add_top_bar(header)

        self.search_bar = Gtk.SearchBar()
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search tasks")
        self.search_bar.set_child(self.search_entry)
        self.search_bar.connect_entry(self.search_entry)
        self.search_btn.bind_property(
            "active",
            self.search_bar,
            "search-mode-enabled",
            GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.search_entry.connect("search-changed", self.on_search_changed)
        toolbar.add_top_bar(self.search_bar)

        bottom_bar = Adw.ViewSwitcherBar(stack=self.root_stack)
        toolbar.add_bottom_bar(bottom_bar)

        toolbar.set_content(self.root_stack)
        self.root_stack.connect("notify::visible-child-name", self._on_page_changed)

    def _build_menu(self) -> Gio.Menu:
        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("Archive Completed", "win.archive-completed")
        section.append("Delete Completed", "win.clear-completed")
        menu.append_section(None, section)
        section2 = Gio.Menu()
        section2.append("Preferences", "app.preferences")
        section2.append("About Flowstate", "app.about")
        menu.append_section(None, section2)
        return menu

    def create_action(self, name, callback, shortcuts=None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            app = self.get_application()
            if app:
                app.set_accels_for_action(f"win.{name}", shortcuts)

    def show_toast(self, title: str, timeout: int = 2) -> None:
        self.toast_overlay.add_toast(Adw.Toast(title=title, timeout=timeout))

    def _on_page_toast(self, _page, title: str) -> None:
        self.show_toast(title)

    def _restore_last_view(self) -> None:
        if self.settings is None:
            return
        name = self.settings.get_string("last-view") or "tasks"
        if name in ("tasks", "planner", "clock"):
            self.root_stack.set_visible_child_name(name)

    def _on_page_changed(self, *_args) -> None:
        name = self.root_stack.get_visible_child_name()
        on_tasks = name == "tasks"
        self.search_btn.set_sensitive(on_tasks)
        if not on_tasks:
            self.search_bar.set_search_mode(False)
        if name == "planner":
            self.set_size_request(900, 600)
        else:
            self.set_size_request(-1, -1)
        if self.settings is not None and name:
            self.settings.set_string("last-view", name)

    def _on_timer_finished(self) -> None:
        self._release_inhibit()
        self.show_toast("Timer finished", timeout=4)
        self.root_stack.set_visible_child_name("clock")
        app = self.get_application()
        if app is None:
            return
        notification = Gio.Notification.new("Timer finished")
        notification.set_body("Your countdown has reached zero.")
        notification.set_priority(Gio.NotificationPriority.HIGH)
        try:
            app.send_notification("timer-finished", notification)
        except Exception:
            pass

    def _on_timer_running(self, running: bool) -> None:
        if running:
            self._acquire_inhibit()
        else:
            self._release_inhibit()

    def _acquire_inhibit(self) -> None:
        """Inhibit idle/suspend while a timer runs; store cookie only if non-zero."""
        app = self.get_application()
        if app is None or self._inhibit_cookie:
            return
        flags = (
            Gtk.ApplicationInhibitFlags.IDLE | Gtk.ApplicationInhibitFlags.SUSPEND
        )
        cookie = app.inhibit(self, flags, "Timer is running")
        # Cookie 0 means inhibit failed / not supported — do not track.
        if cookie:
            self._inhibit_cookie = int(cookie)

    def _release_inhibit(self) -> None:
        """Always clear the cookie, even if uninhibit fails."""
        cookie = self._inhibit_cookie
        self._inhibit_cookie = 0
        if not cookie:
            return
        app = self.get_application()
        if app is None:
            return
        try:
            app.uninhibit(cookie)
        except Exception:
            pass

    def prepare_for_shutdown(self) -> None:
        """Release session inhibits and stop timers (window close or app quit)."""
        self._release_inhibit()
        self.clock_page.dispose_timers()
        self._persist_window_geometry()

    def _persist_window_geometry(self) -> None:
        if self.settings is None:
            return
        if not self.is_maximized():
            width = self.get_width()
            height = self.get_height()
            if width > 0 and height > 0:
                self.settings.set_int("window-width", width)
                self.settings.set_int("window-height", height)
        self.settings.set_boolean("window-maximized", self.is_maximized())

    def _on_maximized_changed(self, *_args) -> None:
        if self.settings is not None:
            self.settings.set_boolean("window-maximized", self.is_maximized())

    def _on_close(self, *_args) -> bool:
        self.prepare_for_shutdown()
        return False

    def on_add(self, *_args) -> None:
        self.root_stack.set_visible_child_name("tasks")
        self.tasks_page.on_add()

    def on_toggle_search(self, *_args) -> None:
        self.root_stack.set_visible_child_name("tasks")
        active = not self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(active)
        if active:
            self.search_entry.grab_focus()

    def on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.tasks_page.set_search_query(entry.get_text())

    def on_clear_completed(self, *_args) -> None:
        self.tasks_page.clear_completed()

    def on_archive_completed(self, *_args) -> None:
        self.tasks_page.archive_completed()
