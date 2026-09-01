# SPDX-License-Identifier: GPL-3.0-or-later
"""Load Supabase credentials from env or XDG config file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gi.repository import GLib

from flowstate.settings import APP_ID

ENV_URL = "FLOWSTATE_SUPABASE_URL"
ENV_KEY = "FLOWSTATE_SUPABASE_ANON_KEY"


@dataclass(frozen=True)
class SyncConfig:
    url: str
    anon_key: str


def _config_file() -> Path:
    config_home = Path(GLib.get_user_config_dir()) / APP_ID
    return config_home / "sync.env"


def load_sync_config() -> SyncConfig | None:
    """Return Supabase URL + anon key when configured."""
    url = os.environ.get(ENV_URL, "").strip()
    key = os.environ.get(ENV_KEY, "").strip()

    path = _config_file()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name == ENV_URL and not url:
                url = value
            elif name == ENV_KEY and not key:
                key = value

    if not url or not key:
        return None
    return SyncConfig(url=url.rstrip("/"), anon_key=key)


def is_sync_configured() -> bool:
    return load_sync_config() is not None


def config_file_path() -> Path:
    return _config_file()
