# Flowstate

A modern GNOME-style desktop app for Debian and other Linux desktops, built with **GTK4** and **libadwaita**.

## Features

- Add tasks quickly (Enter or Ctrl+N)
- Mark complete, edit (double-click or pencil), and delete
- Filter: All / Active / Done
- Search (Ctrl+F)
- **Archive Completed** (keeps history) or permanently delete completed tasks
- **Planner** — daily timeline inspired by Structured (inbox, week strip, task panel with Daily repeat)
- **Clock** — countdown timer and stopwatch (with laps)
- Session inhibit while a timer is running (helps avoid sleep mid-countdown)
- Preferences via GSettings (confirm delete, default filter, window geometry)
- Automatic save under `~/.local/share/io.github.Deadsecnote1.Flowstate/`
- Follows the system light/dark theme

**Scale note:** the task list rebuilds on each change. That is fine for typical personal lists (a few hundred tasks). Prefer archiving completed work if the list grows very large.

**Timers:** closing the app stops running timers. This is not a background alarm daemon.

## Dependencies

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

For building the `.deb` package also install:

```bash
sudo apt install meson ninja-build pkg-config debhelper libgtk-4-dev libadwaita-1-dev libglib2.0-bin
```

## Run from source

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
chmod +x flowstate
./flowstate
```

Source runs may compile GSettings schemas into `~/.cache/...` when they are not installed system-wide. Packaged installs use `/usr/share/glib-2.0/schemas/` instead.

Add **Flowstate** to your application menu:

```bash
./install-local.sh
```

Or:

```bash
PYTHONPATH=src python3 -m flowstate
```

If GTK4 introspection packages are not installed but you have a GNOME Flatpak runtime:

```bash
./run-flatpak.sh
```

## Install with Meson

```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
sudo glib-compile-schemas /usr/share/glib-2.0/schemas
todo
```

## Build a Debian package

```bash
sudo apt install build-essential debhelper meson ninja-build
dpkg-buildpackage -us -uc -b
sudo apt install ../flowstate_1.0.0-1_all.deb
```

## Flatpak

Local build:
```bash
sudo apt install flatpak-builder
flatpak install flathub org.gnome.Sdk//48 org.gnome.Platform//48
flatpak-builder --user --install --force-clean build-flatpak io.github.Deadsecnote1.Flowstate.json
flatpak run io.github.Deadsecnote1.Flowstate
```

**Publish on Flathub:** see [FLATHUB.md](FLATHUB.md).

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Shortcuts

| Shortcut | Action        |
|----------|---------------|
| Ctrl+N   | Focus new task / add |
| Ctrl+F   | Search tasks  |
| Ctrl+Q   | Quit          |
| Enter    | Add task      |

### Clock

Switch to the **Clock** tab in the header:

- **Timer** — set hours/minutes/seconds (or use presets), Start / Pause / Reset
- **Stopwatch** — Start / Pause / Lap / Reset

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — design overview
- [CHANGES.md](CHANGES.md) — architecture refactor notes
- [PRODUCTION.md](PRODUCTION.md) — production readiness checklist

## License

GPL-3.0-or-later

## Source

https://github.com/Deadsecnote1/flowstate
