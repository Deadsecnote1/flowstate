# Architecture refactor changelog
# Date: 2026-08-27

## Summary

Implemented the phased architecture plan: modular views, GSettings state,
completed-task archival, atomic JSON stores, and timer inhibit + stronger
notifications. Compatibility shims keep old import paths working.

## What was wrong in the review (already noted)

- Completed tasks did not grow with *no* escape hatch (`clear_completed` existed).
- Timers do keep running while minimized; they fail on close/suspend.
- `Gio.Notification` was already used on timer finish.

## Phase 1 — Modular view decoupling

### Changes
- Extracted `TasksPage` into `src/flowstate/views/tasks_view.py`.
- Moved Planner UI to `src/flowstate/views/planner_view.py`.
- Moved Clock UI to `src/flowstate/views/clock_view.py`.
- Moved `TodoRow` to `src/flowstate/widgets/todo_row.py`.
- Moved `ClockDigits` to `src/flowstate/widgets/clock_digits.py`.
- Slimmed `window.py` to shell duties only:
  - `Adw.ViewStack` / `ViewSwitcher`
  - Global `Adw.ToastOverlay`
  - Window actions, search bar routing, geometry/settings
- Tasks page emits `request-toast`; window shows toasts.

### Layout after Phase 1+4
```
src/flowstate/
├── main.py
├── window.py
├── settings.py
├── styles.py
├── preferences.py
├── store/
│   ├── __init__.py
│   ├── base.py
│   ├── todo_store.py
│   └── planner_store.py
├── views/
│   ├── __init__.py
│   ├── tasks_view.py
│   ├── planner_view.py
│   └── clock_view.py
└── widgets/
    ├── __init__.py
    ├── todo_row.py
    └── clock_digits.py
```

Compatibility shims (re-exports): `clock.py`, `planner.py`, `planner_store.py`, `row.py`.

## Phase 2 — GSettings

### Schema keys (`data/io.github.Deadsecnote1.Flowstate.gschema.xml`)
| Key | Purpose |
|-----|---------|
| `confirm-delete` | Confirm before deleting a task (wired in TasksPage) |
| `startup-filter` | Default All / Active / Done filter |
| `last-view` | Remember tasks / planner / clock |
| `window-width` / `window-height` | Restore size on launch |
| `window-maximized` | Restore maximized state |

### Code
- New `settings.py` loads installed schema, or compiles from `./data` into
  `~/.cache/io.github.Deadsecnote1.Flowstate/schemas` for source runs.
- Preferences dialog uses `get_settings()`.
- Window restores last view and size; saves on close.

## Phase 3 — Archive completed

### Changes
- `TodoStore.archive_completed()` moves completed items to
  `todos_archive.json` and removes them from `todos.json`.
- Menu:
  - **Archive Completed** — keep history
  - **Delete Completed** — permanent remove (former “Clear Completed”)

## Phase 4 — Store package + atomic writes

### Changes
- `store/base.py`: `Observable`, `atomic_write_json()` (temp + `os.replace`),
  `read_json()`.
- `TodoStore` / `PlannerStore` inherit `Observable` and use atomic writes.
- Public API: `from flowstate.store import TodoStore, PlannerStore, ...`

## Phase 5 — Clock reliability

### Changes
- Timer start/pause/reset/finish notifies window via
  `set_timer_running_changed_callback`.
- While running, window calls `Gtk.Application.inhibit` with
  `IDLE | SUSPEND` so the session is less likely to sleep through a countdown.
- Timer-finished notification sets body + `HIGH` priority (still via
  `Application.send_notification`).

## Files touched (high level)

| Path | Action |
|------|--------|
| `src/flowstate/window.py` | Rewritten as shell |
| `src/flowstate/styles.py` | New — CSS extraction |
| `src/flowstate/settings.py` | New — GSettings helper |
| `src/flowstate/store/*` | New package |
| `src/flowstate/views/*` | New package |
| `src/flowstate/widgets/*` | New package |
| `src/flowstate/preferences.py` | Use settings helper |
| `data/*.gschema.xml` | Extended keys |
| `ARCHITECTURE.md` | Still valid; see this file for refactor delta |
| `CHANGES.md` | This document |

## How to verify

```bash
cd "/path/to/todo"
./flowstate
```

1. Tasks / Planner / Clock tabs still work.
2. Delete a task with Preferences → Confirm before deleting enabled.
3. Complete tasks → menu **Archive Completed** → check
   `~/.local/share/io.github.Deadsecnote1.Flowstate/todos_archive.json`.
4. Start a Timer → system should resist idle suspend until pause/finish.
5. Restart app → last view and window size restore when schemas load.

## 2026-08-27 — Rebrand to Flowstate

- Application display name: **Flowstate**
- App id: `io.github.Deadsecnote1.Flowstate`
- Python package: `src/flowstate/` (was `src/todo/`)
- Binary / Debian package: `flowstate` (was `todo`)
- Data: `~/.local/share/io.github.Deadsecnote1.Flowstate/` (auto-migrates from legacy `io.github.thanushiyan.Todo`)

## 2026-08-27 — GitHub identity

Homepage / bugtracker / Debian maintainer metadata point at
https://github.com/Deadsecnote1/flowstate. CI also runs on `stage`.

Timer duration (spins + first suggestion chip) is saved to
`~/.local/share/io.github.Deadsecnote1.Flowstate/clock.json` and, when available,
GSettings key `timer-duration-seconds`. Closing and reopening the app restores
the last duration instead of resetting to 1 minute.
