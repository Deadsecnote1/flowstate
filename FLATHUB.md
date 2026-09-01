# Publish Flowstate on Flathub

Step-by-step guide to submit **Flowstate** (`io.github.Deadsecnote1.Flowstate`) to [Flathub](https://flathub.org).

## Before you start

Flathub will **reject** the app if any of these are missing:

- [ ] Source on public GitHub: https://github.com/Deadsecnote1/flowstate
- [ ] **Screenshots** in repo + AppStream (see below)
- [ ] Valid `data/io.github.Deadsecnote1.Flowstate.metainfo.xml`
- [ ] App builds with `flatpak-builder` using `flatpak/io.github.Deadsecnote1.Flowstate.yml`
- [ ] GPL-3.0-or-later license visible in repo (`debian/copyright` or `LICENSE`)

---

## Step 1 — Add screenshots (required)

Flathub requires at least **one** screenshot in AppStream.

1. Run the app and capture PNGs (1280×720 or larger):
   ```bash
   flowstate
   # Tasks tab → screenshot
   # Planner tab → screenshot
   # Clock tab → screenshot
   ```
2. Save as:
   ```
   data/screenshots/tasks.png
   data/screenshots/planner.png
   data/screenshots/clock.png
   ```
3. Push to GitHub on branch `main` (or `stage` if that's your default — URLs must match).
4. Metainfo already references:
   `https://raw.githubusercontent.com/Deadsecnote1/flowstate/main/data/screenshots/...`

Validate:
```bash
sudo apt install appstream
appstreamcli validate --no-net data/io.github.Deadsecnote1.Flowstate.metainfo.xml
```

---

## Step 2 — Test Flatpak build locally

Install tools:
```bash
sudo apt install flatpak-builder
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

Get commit SHA for your release tag:
```bash
git fetch --tags
git rev-parse v1.0.0^{commit}
```

Edit `flatpak/io.github.Deadsecnote1.Flowstate.yml` — replace `REPLACE_WITH_GIT_COMMIT_SHA` with that SHA.

Build and install locally:
```bash
cd "/home/thanushiyan/Desktop/developer/Linux apps/todo"
flatpak-builder --user --install --force-clean build-flatpak flatpak/io.github.Deadsecnote1.Flowstate.yml
flatpak run io.github.Deadsecnote1.Flowstate
```

Smoke-test: Tasks, Planner, Clock, Preferences, timer notification.

---

## Step 3 — Submit to Flathub

Flathub uses a **separate manifest repo** (not your app repo).

### Option A — Web (easiest)

1. Open https://github.com/flathub/flathub
2. Use Flathub’s “Submit application” flow (or fork + PR)
3. Add new file: `io.github.Deadsecnote1.Flowstate.yml`
4. Paste contents from `flatpak/io.github.Deadsecnote1.Flowstate.yml` (with real commit SHA)
5. Open Pull Request

### Option B — Git CLI

```bash
git clone https://github.com/flathub/flathub.git
cd flathub
cp "/path/to/flowstate/flatpak/io.github.Deadsecnote1.Flowstate.yml" .
# edit commit SHA
git checkout -b add-flowstate
git add io.github.Deadsecnote1.Flowstate.yml
git commit -m "Add io.github.Deadsecnote1.Flowstate"
git push origin add-flowstate
# Open PR on GitHub
```

### PR description template

```markdown
- [x] I have read the Flathub submission guidelines
- [x] I have built the application locally with flatpak-builder
- [x] AppStream validates
- [x] GPL-3.0-or-later

**App:** Flowstate — tasks, daily planner, timer/stopwatch (GTK4/libadwaita)
**Homepage:** https://github.com/Deadsecnote1/flowstate
```

---

## Step 4 — Review process

- Flathub bot builds your PR on their infrastructure (can take 10–30+ minutes).
- A human reviewer may ask to:
  - Remove unnecessary `finish-args` (keep list minimal)
  - Fix AppStream or screenshots
  - Bump runtime version
- After merge, app appears on Flathub within hours.

Users install with:
```bash
flatpak install flathub io.github.Deadsecnote1.Flowstate
flatpak run io.github.Deadsecnote1.Flowstate
```

---

## Step 5 — Future releases

1. Tag new version on GitHub (`v1.0.1`, etc.)
2. Update `metainfo.xml` `<release>` entry
3. Open PR on **flathub/flathub** updating only:
   - `tag:`
   - `commit:`

Flathub does **not** auto-track your git tags.

---

## Data location (Flatpak)

User data lives at:
```
~/.var/app/io.github.Deadsecnote1.Flowstate/data/io.github.Deadsecnote1.Flowstate/
```
Same JSON files as the `.deb` install, but under the Flatpak sandbox path.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails: no meson | Uses GNOME SDK — ensure runtime 50 installed |
| GSettings / prefs broken | Check dconf finish-args in manifest |
| No notifications | Need `org.freedesktop.Notifications` talk + session bus |
| Screenshot URL 404 | Push PNGs to GitHub before Flathub review |
| App id mismatch | Must be identical everywhere: manifest, desktop, metainfo |

---

## Files in this repo

| File | Purpose |
|------|---------|
| `flatpak/io.github.Deadsecnote1.Flowstate.yml` | Manifest for Flathub PR |
| `io.github.Deadsecnote1.Flowstate.json` | Local dev manifest (`type: dir`) |
| `data/io.github.Deadsecnote1.Flowstate.metainfo.xml` | AppStream for stores |
| `run-flatpak.sh` | Run from source without building |
