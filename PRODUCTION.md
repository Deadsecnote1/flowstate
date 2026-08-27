# Production readiness checklist

What must be done before Todo is treated as a production release
(shippable `.deb` / Flatpak, not just “runs from source”).

Artifact from last build: `dist/todo_1.0.0-1_all.deb` (also `../todo_1.0.0-1_all.deb`).

---

## P0 — Must fix before any public release

### 1. Solidify inhibit cookie tracking — DONE

- [x] Store cookie only when `inhibit()` returns non-zero
- [x] Release on timer pause/finish/reset (via running-changed), window close, app `do_shutdown`
- [x] Guard double-release; clear cookie before `uninhibit`
- [x] Timer `dispose_timers()` emits running=False so inhibit is cleared
- [ ] **You:** manual check — start timer → Quit → confirm the session can idle-sleep

### 2. GSettings schema installation — DONE (packaging)

- [x] Schema installs to `/usr/share/glib-2.0/schemas/` via Meson
- [x] `dh_installgsettings` pulls in gsettings backend dependency; triggers compile on install
- [x] `settings.py` fails gracefully (unwritable cache / missing schema → `None`, prefs disabled)
- [x] Cache compile is documented as **dev-only**
- [ ] **You:** after `sudo apt install ./dist/todo_1.0.0-1_all.deb`, open Preferences and confirm settings persist without `~/.cache` schema compile

### 3. Rebuild packaging from the refactored tree — DONE

- [x] Fresh `dpkg-buildpackage` includes `store/`, `views/`, `widgets/`, `settings.py`
- [x] Stale pre-refactor package replaced (51KB → current tree)
- [ ] **You:** install the new `.deb` and smoke-test (see §7)

### 4. Flatpak / Flathub-oriented manifest — DONE (build locally)

- [x] Hardened `io.github.thanushiyan.Todo.json` (notifications, session inhibit talk-names, GNOME 47)
- [x] `run-flatpak.sh` auto-detects available Platform version
- [ ] **You (optional):** `flatpak-builder --user --install --force-clean build-flatpak io.github.thanushiyan.Todo.json`
- [ ] Flathub submission still optional / later

### 5. Large list scale & UI responsiveness — DOCUMENTED

- [x] README + ARCHITECTURE note: full rebuild is fine for typical lists; archive when large
- [ ] **You (optional):** stress with 500+ tasks if you care about that use case

### 6. Release metadata & AppStream — DONE (with placeholders)

- [x] Maintainer set to `thanushiyan@users.noreply.github.com` (change if you want a real address)
- [x] Package / AppStream / README describe Planner, Clock, archive
- [x] Broken screenshot URLs removed until real assets exist
- [x] Changelog updated for 1.0.0-1
- [ ] **You:** confirm homepage `https://github.com/thanushiyan/todo` exists (or give a new URL)

### 7. Smoke-test matrix — NEEDS YOU

On Mint/Cinnamon and/or GNOME, after installing the `.deb`:

- [ ] Tasks: add / edit / delete / confirm-delete / filters / search
- [ ] Archive Completed → `todos_archive.json`; Delete Completed permanent
- [ ] Planner: inbox, schedule, daily repeat
- [ ] Clock: timer notification; inhibit while running; quit clears inhibit
- [ ] Restart: last view + window size
- [ ] App menu icon visible

```bash
sudo apt install ./dist/todo_1.0.0-1_all.deb
# or: sudo apt install ../todo_1.0.0-1_all.deb
todo
```

---

## P1 — Strongly recommended — MOSTLY DONE

- [x] Unit tests for store / atomic write / corrupt JSON (`make test`)
- [x] CI workflow (`.github/workflows/ci.yml`) — runs once the repo is on GitHub
- [x] Corrupt JSON quarantined to `*.bak` + toast on load
- [x] App shutdown clears inhibit
- [x] Documented: closing the app stops timers
- [ ] Git remote + tag `v1.0.0` (needs your GitHub repo)
- [ ] Desktop smoke-test on a real machine (you)

---

## P2 — Nice to have (post-1.0 OK)

- [ ] `Gtk.ListView` for huge lists
- [ ] Export / import
- [ ] Undo delete / archive
- [ ] Timer sound
- [ ] Translations
- [ ] Flathub submission
- [ ] Screenshots under `data/screenshots/`

---

## Definition of done

**Engineering side for 1.0.0 is ready** once you:

1. Install `dist/todo_1.0.0-1_all.deb` and complete the smoke-test checklist above
2. Confirm or replace maintainer email + GitHub URL
3. (Optional) Push to GitHub so CI runs; tag the release

Dev-only cache schemas and “works from `./todo`” alone do **not** count — use the installed package for the final gate.
