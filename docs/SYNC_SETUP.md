# Flowstate cloud sync — manual setup

Sync is **optional**. The app runs locally without it. Follow these steps once to enable Google sign-in and multi-device sync.

---

## 1. Create a Supabase project (free)

1. Go to [https://supabase.com](https://supabase.com) and sign up.
2. **New project** → pick a name, password, region.
3. Wait for the project to finish provisioning.

---

## 2. Run the database schema

1. Supabase Dashboard → **SQL Editor** → **New query**
2. Paste the contents of [`supabase/schema.sql`](../supabase/schema.sql)
3. Click **Run**

This creates `tasks`, `planner_tasks`, `inbox_items`, triggers, and RLS policies.

If you already ran an older `schema.sql`, also run
[`supabase/patch_lww_client_updated_at.sql`](../supabase/patch_lww_client_updated_at.sql)
once. That adds last-write-wins triggers so a stale device cannot overwrite a
newer delete (or edit) in the cloud.

**Sync order:** clients **pull then push**. Remote tombstones are applied locally
before any local upsert, so deletes propagate across devices.

---

## 3. Enable Google sign-in

### Supabase

1. Dashboard → **Authentication** → **Providers** → **Google** → Enable
2. Leave the Client ID / Secret empty for now (fill after step 3b)

3. Dashboard → **Authentication** → **URL Configuration**
4. Add to **Redirect URLs**:
   ```
   http://127.0.0.1:8765/callback
   ```

### Google Cloud Console

1. [https://console.cloud.google.com](https://console.cloud.google.com) → create or select a project
2. **APIs & Services** → **OAuth consent screen** → configure (External is fine for testing)
3. **Credentials** → **Create credentials** → **OAuth client ID** → **Web application**
4. **Authorized redirect URIs** — add your Supabase callback (from Supabase Google provider page), e.g.:
   ```
   https://YOUR_PROJECT.supabase.co/auth/v1/callback
   ```
5. Copy **Client ID** and **Client secret** into Supabase → Google provider → Save

---

## 4. Configure Flowstate on your Linux machine

### Install Python dependency

Ubuntu blocks `pip install` on system Python (PEP 668). Use **one** of these:

**Option A — venv (recommended):**
```bash
sudo apt install python3.12-venv
cd ~/Desktop/developer/Linux\ apps/todo
./scripts/install-sync-deps.sh
./scripts/run-flowstate.sh
```

**Option B — system Python override:**
```bash
cd ~/Desktop/developer/Linux\ apps/todo
python3 -m pip install --user --break-system-packages -r requirements-sync.txt
PYTHONPATH=src python3 -m flowstate
```

### Create config file

```bash
mkdir -p ~/.config/io.github.Deadsecnote1.Flowstate
cp config/sync.env.example ~/.config/io.github.Deadsecnote1.Flowstate/sync.env
```

Edit `sync.env` with values from Supabase → **Project Settings** → **API**:

- **Project URL** → `FLOWSTATE_SUPABASE_URL`
- **anon public** key → `FLOWSTATE_SUPABASE_ANON_KEY`

---

## 5. Sign in from the app

1. Run Flowstate from source (sync is not bundled in the default `.deb` yet):
   ```bash
   cd ~/Desktop/developer/Linux\ apps/todo
   PYTHONPATH=src python3 -m flowstate
   ```
2. **Preferences → Sync** tab
3. **Sign in with Google**
4. Browser opens → choose account → return to app
5. Status should show `Synced (N pushed, M pulled)` — or use **Sync now** / menu **Sync now**

Edits sync automatically ~2 seconds after you change tasks or planner (when signed in).

---

## Verify sync works

1. Sign in → add a task → wait a few seconds → check Supabase **Table Editor → tasks**
2. Edit a row in Supabase → **Sync now** in Flowstate → task should appear locally
3. Sign out → sign in again → data should reload from cloud

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| “Supabase not configured” | Check `~/.config/io.github.Deadsecnote1.Flowstate/sync.env` |
| “supabase-py is not installed” | Run `pip install --user -r requirements-sync.txt` |
| Browser sign-in fails | Verify redirect URL `http://127.0.0.1:8765/callback` in Supabase |
| Google error redirect_uri_mismatch | Add Supabase callback URL in Google Cloud OAuth client |
| Session expired | Sign out and sign in again |
| Free tier paused | Open Supabase dashboard to wake project (7-day inactivity) |

---

## What syncs

| Data | Synced |
|------|--------|
| Tasks (`todos.json`) | Yes |
| Planner tasks | Yes (not `virt-*` repeat copies) |
| Planner inbox | Yes |
| Window size / last tab (GSettings) | No — per device |
| Clock timer state | No |
| Archived tasks file | No (local backup only) |

---

## Security notes

- Only the **anon** key belongs in `sync.env` (never the service_role key).
- RLS ensures each user sees only their own rows.
- Session tokens are stored in `~/.local/share/io.github.Deadsecnote1.Flowstate/sync_session.json`.
