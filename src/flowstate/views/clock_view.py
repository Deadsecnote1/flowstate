# SPDX-License-Identifier: GPL-3.0-or-later
"""Clock page with countdown timer and stopwatch."""

from __future__ import annotations

import json
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from flowstate.widgets.clock_digits import make_clock_label, set_clock_text

APP_ID = "io.github.Deadsecnote1.Flowstate"


def format_hms(total_ms: int) -> str:
    """Format milliseconds as H:MM:SS or MM:SS for display."""
    total_ms = max(0, int(total_ms))
    hours, rem = divmod(total_ms // 1000, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_stopwatch(total_ms: int) -> str:
    total_ms = max(0, int(total_ms))
    hours, rem = divmod(total_ms // 1000, 3600)
    minutes, seconds = divmod(rem, 60)
    centis = (total_ms % 1000) // 10
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"
    return f"{minutes:02d}:{seconds:02d}.{centis:02d}"


def format_preset_label(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes} min" if not hours and not secs else f"{minutes}m")
    if secs and not hours:
        parts.append(f"{secs}s")
    if not parts:
        return "0 min"
    if len(parts) == 1 and minutes and not hours and not secs:
        return f"{minutes} min"
    return " ".join(parts)


DEFAULT_PRESETS = (60, 300, 600, 1500)  # 1, 5, 10, 25 min


def _clock_state_path() -> Path:
    from flowstate.store.base import resolve_data_dir

    return resolve_data_dir(APP_ID) / "clock.json"


def load_timer_seconds(settings: Gio.Settings | None = None) -> int:
    """Last timer duration in seconds (GSettings, then clock.json, then 60)."""
    if settings is not None:
        schema = settings.get_property("settings-schema")
        if schema is not None and schema.has_key("timer-duration-seconds"):
            value = int(settings.get_int("timer-duration-seconds"))
            if value > 0:
                return value
    path = _clock_state_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            value = int(raw.get("timer_seconds", 0))
            if value > 0:
                return value
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return 60


def save_timer_seconds(seconds: int, settings: Gio.Settings | None = None) -> None:
    seconds = max(0, int(seconds))
    if settings is not None:
        schema = settings.get_property("settings-schema")
        if schema is not None and schema.has_key("timer-duration-seconds"):
            settings.set_int("timer-duration-seconds", seconds)
    path = _clock_state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"timer_seconds": seconds}, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


class TimerView(Gtk.Box):
    """Countdown timer with hour / minute / second spin buttons."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_top(8)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        self._remaining_ms = 0
        self._running = False
        self._tick_id = 0
        self._on_finished = None
        self._on_running_changed = None
        self._preset_btns: list[Gtk.Button] = []
        self._updating_presets = False
        self._settings: Gio.Settings | None = None
        self._persist_enabled = False

        display_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        display_box.set_hexpand(True)
        display_box.set_vexpand(True)
        self.display = make_clock_label("00:00")
        display_box.append(self.display)
        self.append(display_box)

        picker = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        picker.set_halign(Gtk.Align.CENTER)
        picker.add_css_class("timer-picker")

        self.hours = self._spin(0, 23, "h")
        self.minutes = self._spin(0, 59, "m")
        self.seconds = self._spin(0, 59, "s")
        for widget in (self.hours, self.minutes, self.seconds):
            picker.append(widget)
            widget._spin.connect("value-changed", self._on_spin_changed)

        self.append(picker)

        self.presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.presets.set_halign(Gtk.Align.CENTER)
        for _ in range(4):
            btn = Gtk.Button(label="")
            btn.add_css_class("pill")
            btn.add_css_class("flat")
            btn.connect("clicked", self._on_preset_clicked)
            self.presets.append(btn)
            self._preset_btns.append(btn)
        self.append(self.presets)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_halign(Gtk.Align.CENTER)

        self.start_btn = Gtk.Button(label="Start")
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.add_css_class("pill")
        self.start_btn.connect("clicked", self._on_start_pause)

        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.add_css_class("pill")
        self.reset_btn.connect("clicked", self._on_reset)

        controls.append(self.start_btn)
        controls.append(self.reset_btn)
        self.append(controls)

        # Apply saved duration after widgets exist (also refreshes presets).
        self.apply_duration_seconds(load_timer_seconds(None))
        self._persist_enabled = True

    def set_finished_callback(self, callback) -> None:
        self._on_finished = callback

    def set_running_changed_callback(self, callback) -> None:
        self._on_running_changed = callback

    def set_settings(self, settings: Gio.Settings | None) -> None:
        self._settings = settings
        # Re-apply in case GSettings has a newer value than clock.json.
        self._persist_enabled = False
        self.apply_duration_seconds(load_timer_seconds(settings))
        self._persist_enabled = True

    def apply_duration_seconds(self, total_seconds: int) -> None:
        total_seconds = max(0, int(total_seconds))
        hours, rem = divmod(total_seconds, 3600)
        minutes, secs = divmod(rem, 60)
        self._updating_presets = True
        self.hours._spin.set_value(hours)  # type: ignore[attr-defined]
        self.minutes._spin.set_value(minutes)  # type: ignore[attr-defined]
        self.seconds._spin.set_value(secs)  # type: ignore[attr-defined]
        self._updating_presets = False
        self._remaining_ms = 0
        self._sync_display_from_spins()
        self._refresh_presets()

    def _persist_duration(self) -> None:
        if not self._persist_enabled or self._running:
            return
        save_timer_seconds(self._total_seconds_from_spins(), self._settings)

    def _emit_running(self, running: bool) -> None:
        if self._on_running_changed:
            self._on_running_changed(running)

    def _spin(self, minimum: int, maximum: int, suffix: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)
        adj = Gtk.Adjustment(value=0, lower=minimum, upper=maximum, step_increment=1)
        spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        spin.set_width_chars(3)
        spin.set_orientation(Gtk.Orientation.VERTICAL)
        spin.set_wrap(True)
        spin.set_halign(Gtk.Align.CENTER)
        label = Gtk.Label(label=suffix)
        label.add_css_class("dim-label")
        label.add_css_class("caption")
        label.set_halign(Gtk.Align.CENTER)
        box.append(spin)
        box.append(label)
        box._spin = spin  # type: ignore[attr-defined]
        return box

    def _spin_value(self, box: Gtk.Box) -> int:
        return int(box._spin.get_value())  # type: ignore[attr-defined]

    def _set_spin_sensitive(self, sensitive: bool) -> None:
        for box in (self.hours, self.minutes, self.seconds):
            box._spin.set_sensitive(sensitive)  # type: ignore[attr-defined]

    def _total_from_spins(self) -> int:
        h = self._spin_value(self.hours)
        m = self._spin_value(self.minutes)
        s = self._spin_value(self.seconds)
        return ((h * 3600) + (m * 60) + s) * 1000

    def _total_seconds_from_spins(self) -> int:
        return self._total_from_spins() // 1000

    def _preset_seconds_list(self) -> list[int]:
        current = self._total_seconds_from_spins()
        values: list[int] = []
        if current > 0:
            values.append(current)
        for secs in DEFAULT_PRESETS:
            if secs not in values:
                values.append(secs)
            if len(values) >= 4:
                break
        while len(values) < 4:
            for secs in DEFAULT_PRESETS:
                if secs not in values:
                    values.append(secs)
                    break
            else:
                break
        return values[:4]

    def _refresh_presets(self) -> None:
        self._updating_presets = True
        for btn, secs in zip(self._preset_btns, self._preset_seconds_list()):
            btn.set_label(format_preset_label(secs))
            btn._preset_secs = secs  # type: ignore[attr-defined]
        self._updating_presets = False

    def _sync_display_from_spins(self) -> None:
        if not self._running and self._remaining_ms == 0:
            set_clock_text(self.display, format_hms(self._total_from_spins()))

    def _on_spin_changed(self, *_args) -> None:
        if self._running or self._updating_presets:
            return
        self._remaining_ms = 0
        self._sync_display_from_spins()
        self._refresh_presets()
        self._persist_duration()

    def _on_preset_clicked(self, btn: Gtk.Button) -> None:
        secs = getattr(btn, "_preset_secs", 0)
        self._on_preset(btn, secs)

    def _on_preset(self, _btn: Gtk.Button, seconds: int) -> None:
        if self._running:
            return
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        self._updating_presets = True
        self.hours._spin.set_value(hours)  # type: ignore[attr-defined]
        self.minutes._spin.set_value(minutes)  # type: ignore[attr-defined]
        self.seconds._spin.set_value(secs)  # type: ignore[attr-defined]
        self._updating_presets = False
        self._remaining_ms = 0
        self._sync_display_from_spins()
        self._refresh_presets()
        self._persist_duration()

    def _on_start_pause(self, *_args) -> None:
        if self._running:
            self._pause()
            return
        if self._remaining_ms <= 0:
            self._remaining_ms = self._total_from_spins()
        if self._remaining_ms <= 0:
            return
        self._running = True
        self._emit_running(True)
        self._set_spin_sensitive(False)
        self.start_btn.set_label("Pause")
        self.start_btn.remove_css_class("suggested-action")
        set_clock_text(self.display, format_hms(self._remaining_ms))
        self._tick_id = GLib.timeout_add(100, self._tick)

    def _pause(self) -> None:
        self._running = False
        self._emit_running(False)
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0
        self.start_btn.set_label("Resume")
        self.start_btn.add_css_class("suggested-action")

    def _on_reset(self, *_args) -> None:
        self._stop_tick()
        was_running = self._running
        self._running = False
        if was_running:
            self._emit_running(False)
        self._remaining_ms = 0
        self._set_spin_sensitive(True)
        self.start_btn.set_label("Start")
        self.start_btn.add_css_class("suggested-action")
        self._sync_display_from_spins()
        self._refresh_presets()

    def _stop_tick(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _tick(self) -> bool:
        if not self._running:
            return False
        self._remaining_ms = max(0, self._remaining_ms - 100)
        set_clock_text(self.display, format_hms(self._remaining_ms))
        if self._remaining_ms <= 0:
            self._running = False
            self._emit_running(False)
            self._tick_id = 0
            self._set_spin_sensitive(True)
            self.start_btn.set_label("Start")
            self.start_btn.add_css_class("suggested-action")
            if self._on_finished:
                self._on_finished()
            return False
        return True

    def dispose_timers(self) -> None:
        was_running = self._running
        self._stop_tick()
        self._running = False
        if was_running:
            self._emit_running(False)


class StopwatchView(Gtk.Box):
    """Stopwatch with start / pause / reset and lap times."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_margin_top(8)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        self._elapsed_ms = 0
        self._running = False
        self._tick_id = 0
        self._laps: list[int] = []

        display_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        display_box.set_hexpand(True)
        display_box.set_vexpand(True)
        self.display = make_clock_label("00:00.00")
        display_box.append(self.display)
        self.append(display_box)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_halign(Gtk.Align.CENTER)

        self.start_btn = Gtk.Button(label="Start")
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.add_css_class("pill")
        self.start_btn.connect("clicked", self._on_start_pause)

        self.lap_btn = Gtk.Button(label="Lap")
        self.lap_btn.add_css_class("pill")
        self.lap_btn.set_sensitive(False)
        self.lap_btn.connect("clicked", self._on_lap)

        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.add_css_class("pill")
        self.reset_btn.connect("clicked", self._on_reset)

        controls.append(self.start_btn)
        controls.append(self.lap_btn)
        controls.append(self.reset_btn)
        self.append(controls)

        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(100)
        scrolled.set_vexpand(True)
        self.lap_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.lap_list.add_css_class("boxed-list")
        scrolled.set_child(self.lap_list)
        self.append(scrolled)

    def _on_start_pause(self, *_args) -> None:
        if self._running:
            self._pause()
            return
        self._running = True
        self.start_btn.set_label("Pause")
        self.start_btn.remove_css_class("suggested-action")
        self.lap_btn.set_sensitive(True)
        self._tick_id = GLib.timeout_add(10, self._tick)

    def _pause(self) -> None:
        self._running = False
        self._stop_tick()
        self.start_btn.set_label("Resume")
        self.start_btn.add_css_class("suggested-action")
        self.lap_btn.set_sensitive(False)

    def _on_reset(self, *_args) -> None:
        self._stop_tick()
        self._running = False
        self._elapsed_ms = 0
        self._laps.clear()
        set_clock_text(self.display, "00:00.00")
        self.start_btn.set_label("Start")
        self.start_btn.add_css_class("suggested-action")
        self.lap_btn.set_sensitive(False)
        while (child := self.lap_list.get_first_child()) is not None:
            self.lap_list.remove(child)

    def _on_lap(self, *_args) -> None:
        if not self._running:
            return
        self._laps.append(self._elapsed_ms)
        n = len(self._laps)
        prev = self._laps[-2] if n > 1 else 0
        split = self._elapsed_ms - prev
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        left = Gtk.Label(label=f"Lap {n}", xalign=0, hexpand=True)
        right = Gtk.Label(label=format_stopwatch(self._elapsed_ms), xalign=1)
        right.add_css_class("dim-label")
        split_lbl = Gtk.Label(label=f"+{format_stopwatch(split)}", xalign=1)
        split_lbl.add_css_class("caption")
        split_lbl.add_css_class("dim-label")
        box.append(left)
        box.append(split_lbl)
        box.append(right)
        row.set_child(box)
        self.lap_list.prepend(row)

    def _stop_tick(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _tick(self) -> bool:
        if not self._running:
            return False
        self._elapsed_ms += 10
        set_clock_text(self.display, format_stopwatch(self._elapsed_ms))
        return True

    def dispose_timers(self) -> None:
        self._stop_tick()


class ClockPage(Gtk.Box):
    """Clock page hosting Timer and Stopwatch tabs."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.timer = TimerView()
        self.stopwatch = StopwatchView()

        self.stack = Adw.ViewStack(vexpand=True)
        self.stack.add_titled_with_icon(
            self.timer, "timer", "Timer", "alarm-symbolic"
        )
        self.stack.add_titled_with_icon(
            self.stopwatch, "stopwatch", "Stopwatch", "stopwatch-symbolic"
        )

        switcher = Adw.ViewSwitcher(
            stack=self.stack,
            policy=Adw.ViewSwitcherPolicy.WIDE,
        )
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_margin_top(8)
        switcher.set_margin_bottom(4)

        self.append(switcher)
        self.append(self.stack)

        bar = Adw.ViewSwitcherBar(stack=self.stack)
        self.append(bar)

    def set_timer_finished_callback(self, callback) -> None:
        self.timer.set_finished_callback(callback)

    def set_timer_running_changed_callback(self, callback) -> None:
        self.timer.set_running_changed_callback(callback)

    def set_settings(self, settings) -> None:
        self.timer.set_settings(settings)

    def dispose_timers(self) -> None:
        self.timer.dispose_timers()
        self.stopwatch.dispose_timers()
