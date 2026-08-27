# Flowstate architecture

Design of the GTK4 / libadwaita desktop app: layered UI, dual persistence stores, and Debian packaging. Source tree: `src/flowstate/`.

| | |
|---|---|
| Primary views | 3 — Tasks, Planner, Clock |
| JSON stores | 2 — `todos.json`, `planner.json` (+ optional `todos_archive.json`) |
| UI toolkit | GTK4 + libadwaita |
| Packaging | Meson / Debian `.deb` |

## Core idea

One `Adw.Application` owns a single window. The window is a `ViewStack` of independent feature pages (Tasks, Planner, Clock). Each feature that needs persistence talks to its own store; stores write XDG JSON and notify subscribers so the UI refreshes without a global event bus.

## Layout

```
src/flowstate/
├── main.py
├── window.py              # Shell: ViewStack, toasts, inhibit, geometry
├── settings.py            # GSettings helper
├── styles.py              # Shared CSS
├── preferences.py
├── store/
│   ├── base.py            # Observable + atomic JSON write
│   ├── todo_store.py      # Todos + archive
│   └── planner_store.py
├── views/
│   ├── tasks_view.py
│   ├── planner_view.py
│   └── clock_view.py
└── widgets/
    ├── todo_row.py
    └── clock_digits.py
```

Compatibility shims re-export old module paths: `clock.py`, `planner.py`, `planner_store.py`, `row.py`.

See [CHANGES.md](CHANGES.md) for the 2026-08-27 architecture refactor details.

```
todo / __main__
    → FlowstateApplication (main.py)
        → FlowstateWindow + ViewStack (window.py)
            → TasksPage   → TodoStore    → todos.json / todos_archive.json
            → PlannerPage → PlannerStore → planner.json
            → ClockPage   → (ephemeral; inhibit while timer runs)
                ↓
         ~/.local/share/io.github.Deadsecnote1.Flowstate/
```

## Module map

| Module | Role | Depends on |
|--------|------|------------|
| `main.py` | GApplication lifecycle, About, Preferences | Adw, FlowstateWindow |
| `window.py` | Shell: ViewSwitcher, toasts, actions, inhibit, geometry | store, views, settings, styles |
| `settings.py` | Load installed or compile-from-source GSettings | Gio |
| `styles.py` | Shared application CSS | — |
| `store/` | Todo + Planner stores, atomic JSON, Observable | GLib paths |
| `views/` | Tasks, Planner, Clock feature pages | store, widgets |
| `widgets/` | `TodoRow`, `ClockDigits` | Gtk |
| `preferences.py` | Adw preferences dialog | settings |

## Feature architecture

### Tasks

Classic list UX: entry field, All / Active / Done filters, search, toasts.

`TodoStore` holds items in memory, persists on every mutation, and fans out via `subscribe()` so `refresh()` rebuilds rows. Completed items can be archived to `todos_archive.json` or permanently deleted.

Concepts: `TodoItem`, `TodoRow`, `todos.json`, `todos_archive.json`

### Planner (Structured-inspired)

Three-pane layout: Inbox (left), day timeline (center), coral TaskEditor panel (right).

`PlannerStore.tasks_for_day()` merges dated tasks with `repeat=daily` virtual instances. Editor emits saved / deleted / closed; the page owns store writes.

Concepts: `PlanTask`, `TaskEditor`, `planner.json`

### Clock

Nested ViewStack: Timer (countdown + dynamic presets) and Stopwatch (laps).

Digits are drawn with Cairo (`ClockDigits`) so size is theme-independent. GLib timeouts drive ticks; a finished timer raises a toast + high-priority notification. While a timer is running the shell holds an idle/suspend inhibit.

Concepts: `TimerView`, `StopwatchView` (no disk I/O)

## Data & state

### Persistence

Stores use `~/.local/share/io.github.Deadsecnote1.Flowstate/`:

| File | Contents |
|------|----------|
| `todos.json` | `items[]` — id, title, completed, notes, created_at |
| `todos_archive.json` | Archived completed tasks (append-only history) |
| `planner.json` | `tasks[]` + `inbox[]` — schedule, duration, repeat, color |

No database. Writes use temp file + `os.replace` (atomic). Observer pattern: stores keep listeners; pages call `subscribe(refresh)`.

Task list UIs rebuild children on each `refresh()` — fine for typical personal lists (&lt; ~200–300 tasks). Archive completed items if the active list grows large.

**Why split stores?** Todo list and day planner have different schemas and query patterns.

### GSettings

Schema `io.github.Deadsecnote1.Flowstate`: confirm-delete, startup-filter, last-view, window size/maximized. Source runs compile the schema into `~/.cache/.../schemas` when not installed system-wide.

## Design decisions

### GTK4 + libadwaita

Native Debian/GNOME look, system dark/light, keyboard shortcuts, and `.desktop` / AppStream integration.

### ViewStack navigation

Tasks / Planner / Clock share one window and header. Feature pages stay isolated; the shell wires actions, CSS, toasts, and inhibit.

### Cairo clock digits

Theme CSS failed to force large type on Mint. A `DrawingArea` sizes glyphs to ~78% of allocated height.

### Planner visual language

Planner CSS uses a Structured-inspired dark surface and coral accent (`#E8837A`) scoped to `planner-*` classes.

## Packaging & desktop integration

| Artifact | Purpose |
|----------|---------|
| `meson.build` / `todo.in` | Install binary + Python package |
| `data/*.desktop` | App menu launcher + Icon name |
| `data/*.metainfo.xml` | AppStream / Software store metadata |
| `data/*.gschema.xml` | GSettings keys |
| `data/icons/hicolor/**` | SVG + PNG sizes for Cinnamon/Mint |
| `debian/*` | `dpkg-buildpackage` → `todo_*.deb` |
| `install-local.sh` | User-local `.desktop` + icons without sudo |

App id `io.github.Deadsecnote1.Flowstate` ties D-Bus uniqueness, icons, schemas, and XDG paths together.

Legacy data from `io.github.thanushiyan.Todo` is copied automatically on first launch if the new data directory is empty.

---

*Also available as a Cursor canvas: `docs/flowstate-architecture.canvas.tsx`*
