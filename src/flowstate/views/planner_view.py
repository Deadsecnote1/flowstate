# SPDX-License-Identifier: GPL-3.0-or-later
"""Structured-inspired daily planner page."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk

from flowstate.store import PlanTask, PlannerStore

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

DURATION_PRESETS = (
    (1, "1m"),
    (15, "15m"),
    (30, "30m"),
    (45, "45m"),
    (60, "1hr"),
    (90, "1hr 30m"),
)


def format_clock(minutes: int) -> str:
    minutes = int(minutes) % (24 * 60)
    h, m = divmod(minutes, 60)
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def format_duration(minutes: int) -> str:
    minutes = max(1, int(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return "1hr" if h == 1 else f"{h}h"
    return f"{m}m"


class TaskEditor(Gtk.Box):
    """Right-side Structured-style task panel."""

    __gsignals__ = {
        "saved": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "closed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("planner-panel")
        self.set_size_request(340, -1)
        self.set_hexpand(False)
        self._task: PlanTask | None = None
        self._is_new = True
        self._building = False

        self.header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.header.add_css_class("planner-panel-header")
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_row.set_margin_start(14)
        top_row.set_margin_end(10)
        top_row.set_margin_top(14)
        top_row.set_margin_bottom(14)

        self.icon_pill = Gtk.Label(label="☀")
        self.icon_pill.add_css_class("planner-icon-pill")
        top_row.append(self.icon_pill)

        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        titles.set_hexpand(True)
        self.time_summary = Gtk.Label(xalign=0)
        self.time_summary.add_css_class("planner-header-time")
        self.title_entry = Gtk.Entry()
        self.title_entry.add_css_class("planner-title-entry")
        self.title_entry.set_placeholder_text("Task title")
        self.repeat_hint = Gtk.Label(label="", xalign=0)
        self.repeat_hint.add_css_class("planner-header-repeat")
        titles.append(self.time_summary)
        titles.append(self.title_entry)
        titles.append(self.repeat_hint)
        top_row.append(titles)

        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("circular")
        close_btn.add_css_class("flat")
        close_btn.add_css_class("planner-header-btn")
        close_btn.connect("clicked", lambda *_: self.emit("closed"))
        top_row.append(close_btn)
        self.header.append(top_row)
        self.append(self.header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.add_css_class("planner-panel-body")
        body.set_margin_start(12)
        body.set_margin_end(12)
        body.set_margin_top(12)
        body.set_vexpand(True)

        date_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        date_row.add_css_class("planner-row")
        date_row.append(Gtk.Image.new_from_icon_name("x-office-calendar-symbolic"))
        self.date_label = Gtk.Label(xalign=0, hexpand=True)
        date_row.append(self.date_label)
        self.all_day = Gtk.CheckButton(label="All-Day")
        self.all_day.connect("toggled", self._on_all_day)
        date_row.append(self.all_day)
        body.append(date_row)

        self.time_btn = Gtk.Button()
        self.time_btn.add_css_class("planner-row")
        self.time_btn.add_css_class("flat")
        time_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        time_inner.append(Gtk.Image.new_from_icon_name("preferences-system-time-symbolic"))
        self.time_label = Gtk.Label(xalign=0, hexpand=True)
        time_inner.append(self.time_label)
        self.time_btn.set_child(time_inner)
        self.time_btn.connect("clicked", self._toggle_time_box)
        body.append(self.time_btn)

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.time_box.add_css_class("planner-time-box")
        self.time_box.set_visible(False)

        time_inputs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        time_inputs.set_halign(Gtk.Align.CENTER)
        self.start_hour = self._spin(0, 23, 9)
        self.start_min = self._spin(0, 59, 0)
        self.end_hour = self._spin(0, 23, 10)
        self.end_min = self._spin(0, 59, 0)
        time_inputs.append(self._labeled_spin("Start", self.start_hour, self.start_min))
        arrow = Gtk.Label(label="→")
        arrow.add_css_class("dim-label")
        time_inputs.append(arrow)
        time_inputs.append(self._labeled_spin("End", self.end_hour, self.end_min))
        self.time_box.append(time_inputs)

        presets_lbl = Gtk.Label(label="Presets", xalign=0)
        presets_lbl.add_css_class("dim-label")
        self.time_box.append(presets_lbl)

        preset_grid = Gtk.FlowBox()
        preset_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        preset_grid.set_max_children_per_line(3)
        preset_grid.set_min_children_per_line(3)
        preset_grid.set_homogeneous(True)
        self._preset_buttons: list[Gtk.Button] = []
        for mins, label in DURATION_PRESETS:
            btn = Gtk.Button(label=label)
            btn.add_css_class("planner-preset")
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_preset, mins)
            self._preset_buttons.append(btn)
            preset_grid.append(btn)
        self.time_box.append(preset_grid)
        body.append(self.time_box)

        repeat_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        repeat_row.add_css_class("planner-row")
        repeat_row.append(Gtk.Image.new_from_icon_name("media-playlist-repeat-symbolic"))
        self.daily_btn = Gtk.ToggleButton(label="Daily")
        self.daily_btn.add_css_class("planner-daily")
        self.daily_btn.add_css_class("pill")
        self.daily_btn.connect("toggled", self._on_daily_toggled)
        repeat_row.append(self.daily_btn)
        body.append(repeat_row)

        notes_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        notes_frame.add_css_class("planner-row")
        self.notes = Gtk.TextView()
        self.notes.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.notes.set_size_request(-1, 90)
        self.notes.add_css_class("planner-notes")
        notes_frame.append(self.notes)
        hint = Gtk.Label(
            label="Add notes, meeting links or phone numbers...",
            xalign=0,
        )
        hint.add_css_class("dim-label")
        hint.add_css_class("caption")
        notes_frame.append(hint)
        body.append(notes_frame)
        self.append(body)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer.add_css_class("planner-panel-footer")
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        footer.set_margin_bottom(12)
        footer.set_margin_top(4)

        self.delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_btn.add_css_class("circular")
        self.delete_btn.add_css_class("flat")
        self.delete_btn.connect("clicked", lambda *_: self.emit("deleted"))
        footer.append(self.delete_btn)
        footer.append(Gtk.Box(hexpand=True))

        self.save_btn = Gtk.Button(label="Create Task")
        self.save_btn.add_css_class("planner-save")
        self.save_btn.add_css_class("pill")
        self.save_btn.connect("clicked", self._on_save)
        footer.append(self.save_btn)
        self.append(footer)

        for spin in (self.start_hour, self.start_min, self.end_hour, self.end_min):
            spin.connect("value-changed", self._on_time_changed)

    def _spin(self, lo: int, hi: int, value: int) -> Gtk.SpinButton:
        adj = Gtk.Adjustment(value=value, lower=lo, upper=hi, step_increment=1)
        spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        spin.set_width_chars(3)
        return spin

    def _labeled_spin(
        self, title: str, hour: Gtk.SpinButton, minute: Gtk.SpinButton
    ) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lab = Gtk.Label(label=title)
        lab.add_css_class("caption")
        lab.add_css_class("dim-label")
        box.append(lab)
        row = Gtk.Box(spacing=4)
        row.append(hour)
        row.append(Gtk.Label(label=":"))
        row.append(minute)
        box.append(row)
        return box

    def open_task(self, task: PlanTask, is_new: bool = False) -> None:
        self._building = True
        self._task = task
        self._is_new = is_new
        self.title_entry.set_text(task.title)
        self.all_day.set_active(task.all_day)
        self.daily_btn.set_active(task.repeat == "daily")
        self.start_hour.set_value(task.start_min // 60)
        self.start_min.set_value(task.start_min % 60)
        self.end_hour.set_value(task.end_min // 60)
        self.end_min.set_value(task.end_min % 60)
        self.notes.get_buffer().set_text(task.notes or "")
        self.save_btn.set_label("Create Task" if is_new else "Update Task")
        self.delete_btn.set_visible(not is_new and not task.id.startswith("virt-"))
        self.time_box.set_visible(False)
        self._refresh_labels()
        self._building = False
        self.set_visible(True)

    def _start_end(self) -> tuple[int, int]:
        start = int(self.start_hour.get_value()) * 60 + int(self.start_min.get_value())
        end = int(self.end_hour.get_value()) * 60 + int(self.end_min.get_value())
        if end <= start:
            end = start + 1
        return start, end

    def _refresh_labels(self) -> None:
        if not self._task:
            return
        day = date.fromisoformat(self._task.date)
        today = date.today()
        if day == today:
            prefix = "Today"
        elif day == today + timedelta(days=1):
            prefix = "Tomorrow"
        else:
            prefix = WEEKDAYS[day.weekday()]
        self.date_label.set_text(
            f"{prefix}, {WEEKDAYS[day.weekday()]}, {day.strftime('%b')} {day.day}"
        )

        if self.all_day.get_active():
            summary = "All day"
            self.time_label.set_text("All day")
        else:
            start, end = self._start_end()
            dur = format_duration(end - start)
            summary = f"{format_clock(start)} - {format_clock(end)} ({dur})"
            self.time_label.set_text(f"{format_clock(start)} - {format_clock(end)}")
        self.time_summary.set_text(summary)
        self.repeat_hint.set_text("Every day" if self.daily_btn.get_active() else "")

        start, end = self._start_end()
        dur = end - start
        for btn, (mins, _) in zip(self._preset_buttons, DURATION_PRESETS):
            if mins == dur:
                btn.add_css_class("planner-preset-active")
            else:
                btn.remove_css_class("planner-preset-active")

    def _toggle_time_box(self, *_args) -> None:
        self.time_box.set_visible(not self.time_box.get_visible())

    def _on_all_day(self, *_args) -> None:
        self.time_btn.set_sensitive(not self.all_day.get_active())
        self._refresh_labels()

    def _on_daily_toggled(self, *_args) -> None:
        self._refresh_labels()

    def _on_time_changed(self, *_args) -> None:
        if not self._building:
            self._refresh_labels()

    def _on_preset(self, _btn: Gtk.Button, mins: int) -> None:
        start, _ = self._start_end()
        end = min(start + mins, 24 * 60 - 1)
        self._building = True
        self.end_hour.set_value(end // 60)
        self.end_min.set_value(end % 60)
        self._building = False
        self._refresh_labels()

    def _on_save(self, *_args) -> None:
        if not self._task:
            return
        title = self.title_entry.get_text().strip() or "Untitled"
        start, end = self._start_end()
        buf = self.notes.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self._task.title = title
        self._task.all_day = self.all_day.get_active()
        self._task.start_min = start
        self._task.end_min = end
        self._task.notes = text
        self._task.repeat = "daily" if self.daily_btn.get_active() else "none"
        self.emit("saved")

    @property
    def is_new(self) -> bool:
        return self._is_new

    def current_task(self) -> PlanTask | None:
        return self._task


class PlannerPage(Gtk.Box):
    """Daily planner with inbox, timeline, and task panel."""

    def __init__(self, store: PlannerStore | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class("planner-root")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.store = store or PlannerStore()
        self._day = date.today()

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        left.add_css_class("planner-inbox")
        left.set_size_request(240, -1)
        left.set_margin_start(12)
        left.set_margin_top(12)
        left.set_margin_bottom(12)

        inbox_btn = Gtk.Button(label="Inbox")
        inbox_btn.add_css_class("planner-inbox-btn")
        inbox_btn.add_css_class("pill")
        left.append(inbox_btn)

        self.inbox_entry = Gtk.Entry(placeholder_text="Add a new inbox task...")
        self.inbox_entry.add_css_class("planner-inbox-entry")
        self.inbox_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "list-add-symbolic"
        )
        self.inbox_entry.connect("activate", self._add_inbox)
        self.inbox_entry.connect("icon-press", lambda *_: self._add_inbox())
        left.append(self.inbox_entry)

        self.inbox_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.inbox_list.add_css_class("planner-inbox-list")
        scrolled_inbox = Gtk.ScrolledWindow(vexpand=True)
        scrolled_inbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_inbox.set_child(self.inbox_list)
        left.append(scrolled_inbox)

        self.inbox_empty = Adw.StatusPage(
            icon_name="emoji-symbols-symbolic",
            title="Your Unstructured Thoughts",
            description=(
                "Capture tasks and thoughts as they come. "
                "Move them to your timeline when you are ready."
            ),
        )
        self.inbox_empty.add_css_class("planner-inbox-empty")
        left.append(self.inbox_empty)
        self.append(left)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        center.set_hexpand(True)
        center.set_vexpand(True)
        center.set_margin_top(12)
        center.set_margin_bottom(12)
        center.set_margin_end(8)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.month_label = Gtk.Label(xalign=0)
        self.month_label.add_css_class("planner-month")
        self.month_label.set_hexpand(True)
        nav.append(self.month_label)
        prev = Gtk.Button(icon_name="go-previous-symbolic")
        prev.add_css_class("flat")
        prev.connect("clicked", lambda *_: self._shift_day(-1))
        next_btn = Gtk.Button(icon_name="go-next-symbolic")
        next_btn.add_css_class("flat")
        next_btn.connect("clicked", lambda *_: self._shift_day(1))
        nav.append(prev)
        nav.append(next_btn)
        center.append(nav)

        self.week_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.week_box.add_css_class("planner-week")
        center.append(self.week_box)

        timeline_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        timeline_frame.add_css_class("planner-timeline-frame")
        timeline_frame.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.timeline = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.timeline.add_css_class("planner-timeline")
        self.timeline.set_margin_start(16)
        self.timeline.set_margin_end(16)
        self.timeline.set_margin_top(16)
        self.timeline.set_margin_bottom(16)
        scrolled.set_child(self.timeline)
        timeline_frame.append(scrolled)

        fab_box = Gtk.Box(halign=Gtk.Align.END, valign=Gtk.Align.END)
        fab_box.set_margin_end(16)
        fab_box.set_margin_bottom(16)
        fab = Gtk.Button(icon_name="list-add-symbolic")
        fab.add_css_class("planner-fab")
        fab.add_css_class("circular")
        fab.set_tooltip_text("New planned task")
        fab.connect("clicked", self._new_task)
        fab_box.append(fab)

        overlay = Gtk.Overlay()
        overlay.set_child(timeline_frame)
        overlay.add_overlay(fab_box)
        center.append(overlay)
        self.append(center)

        self.editor = TaskEditor()
        self.editor.set_visible(False)
        self.editor.connect("saved", self._on_editor_saved)
        self.editor.connect("deleted", self._on_editor_deleted)
        self.editor.connect("closed", self._on_editor_closed)
        self.editor.set_margin_top(12)
        self.editor.set_margin_bottom(12)
        self.editor.set_margin_end(12)
        self.append(self.editor)

        self.store.subscribe(self.refresh)
        self.refresh()

    def _shift_day(self, delta: int) -> None:
        self._day += timedelta(days=delta)
        self.refresh()

    def _add_inbox(self, *_args) -> None:
        self.store.add_inbox(self.inbox_entry.get_text())
        self.inbox_entry.set_text("")

    def _new_task(self, *_args) -> None:
        now = datetime.now()
        start = now.hour * 60 + (0 if now.minute < 30 else 30)
        task = PlanTask.create("New task", self._day, start, start + 30)
        self.editor.open_task(task, is_new=True)

    def _on_editor_saved(self, *_args) -> None:
        task = self.editor.current_task()
        if not task:
            return
        if self.editor.is_new:
            self.store.add(task)
        else:
            self.store.update(task)
        self.editor.set_visible(False)

    def _on_editor_deleted(self, *_args) -> None:
        task = self.editor.current_task()
        if task:
            self.store.remove(task.id)
        self.editor.set_visible(False)

    def _on_editor_closed(self, *_args) -> None:
        self.editor.set_visible(False)

    def refresh(self) -> None:
        self.month_label.set_text(self._day.strftime("%B %Y"))
        self._rebuild_week()
        self._rebuild_timeline()
        self._rebuild_inbox()

    def _rebuild_week(self) -> None:
        while (child := self.week_box.get_first_child()) is not None:
            self.week_box.remove(child)
        start = self._day - timedelta(days=(self._day.weekday() + 1) % 7)
        for i in range(7):
            day = start + timedelta(days=i)
            btn = Gtk.ToggleButton()
            btn.add_css_class("planner-day-chip")
            btn.add_css_class("flat")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.CENTER)
            name = Gtk.Label(label=day.strftime("%a")[:3])
            name.add_css_class("caption")
            num = Gtk.Label(label=str(day.day))
            num.add_css_class("planner-day-num")
            col.append(name)
            col.append(num)
            btn.set_child(col)
            btn.set_active(day == self._day)
            if day == date.today():
                btn.add_css_class("planner-day-today")
            btn.connect("toggled", self._on_day_chip, day)
            btn.set_hexpand(True)
            self.week_box.append(btn)

    def _on_day_chip(self, btn: Gtk.ToggleButton, day: date) -> None:
        if btn.get_active() and day != self._day:
            self._day = day
            self.refresh()

    def _rebuild_inbox(self) -> None:
        while (child := self.inbox_list.get_first_child()) is not None:
            self.inbox_list.remove(child)
        items = self.store.inbox
        self.inbox_empty.set_visible(not items)
        for item in items:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=8)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(8)
            box.set_margin_end(8)
            lab = Gtk.Label(label=item["title"], xalign=0, hexpand=True)
            box.append(lab)
            schedule = Gtk.Button(label="Plan")
            schedule.add_css_class("pill")
            schedule.add_css_class("flat")
            schedule.connect("clicked", self._schedule_inbox, item)
            box.append(schedule)
            row.set_child(box)
            self.inbox_list.append(row)

    def _schedule_inbox(self, _btn: Gtk.Button, item: dict) -> None:
        now = datetime.now()
        start = now.hour * 60 + (0 if now.minute < 30 else 30)
        task = PlanTask.create(item["title"], self._day, start, start + 30)
        self.store.remove_inbox(item["id"])
        self.editor.open_task(task, is_new=True)

    def _rebuild_timeline(self) -> None:
        while (child := self.timeline.get_first_child()) is not None:
            self.timeline.remove(child)

        tasks = self.store.tasks_for_day(self._day)
        if not tasks:
            empty = Adw.StatusPage(
                icon_name="x-office-calendar-symbolic",
                title="Nothing planned",
                description="Tap + to structure your day.",
            )
            self.timeline.append(empty)
            return

        for idx, task in enumerate(tasks):
            row = Gtk.Button()
            row.add_css_class("flat")
            row.add_css_class("planner-event")
            row.connect("clicked", self._open_task, task)

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            icon = Gtk.Label(label="☀" if task.color != "blue" else "☾")
            icon.add_css_class("planner-event-icon")
            icon.add_css_class(
                "planner-event-icon-blue"
                if task.color == "blue"
                else "planner-event-icon-coral"
            )
            box.append(icon)

            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            texts.set_hexpand(True)
            tlabel = Gtk.Label(
                label=format_clock(task.start_min) if not task.all_day else "All day",
                xalign=0,
            )
            tlabel.add_css_class("dim-label")
            tlabel.add_css_class("caption")
            title = Gtk.Label(label=task.title, xalign=0)
            title.add_css_class("planner-event-title")
            if task.completed:
                title.add_css_class("dim-label")
            texts.append(tlabel)
            texts.append(title)
            box.append(texts)

            check = Gtk.CheckButton(active=task.completed)
            check.connect("toggled", self._toggle_task, task)
            box.append(check)
            row.set_child(box)
            self.timeline.append(row)

            if idx < len(tasks) - 1:
                nxt = tasks[idx + 1]
                gap = max(0, nxt.start_min - task.end_min)
                if gap >= 30:
                    gap_lbl = Gtk.Label(
                        label=f"Major strides in {format_duration(gap)}?",
                        xalign=0.5,
                    )
                    gap_lbl.add_css_class("planner-gap")
                    gap_lbl.set_margin_top(6)
                    gap_lbl.set_margin_bottom(6)
                    self.timeline.append(gap_lbl)

    def _open_task(self, _btn: Gtk.Button, task: PlanTask) -> None:
        copy = PlanTask(**{**task.__dict__})
        self.editor.open_task(copy, is_new=False)

    def _toggle_task(self, btn: Gtk.CheckButton, task: PlanTask) -> None:
        if task.id.startswith("virt-"):
            task.completed = btn.get_active()
            self.store.update(task)
            return
        real = self.store.get(task.id)
        if real:
            real.completed = btn.get_active()
            self.store.update(real)
