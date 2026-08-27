# SPDX-License-Identifier: GPL-3.0-or-later
"""GSettings helper with optional schema load from the source tree."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from gi.repository import Gio

APP_ID = "io.github.Deadsecnote1.Flowstate"


def _project_schema_dir() -> Path | None:
    # src/flowstate/settings.py -> repo root/data
    here = Path(__file__).resolve()
    candidate = here.parents[2] / "data"
    schema = candidate / f"{APP_ID}.gschema.xml"
    if schema.exists():
        return candidate
    return None


def get_settings() -> Gio.Settings | None:
    """Return Gio.Settings when a compiled schema is available.

    Production installs must ship the schema under
    ``/usr/share/glib-2.0/schemas/`` (compiled by the package postinst /
    ``glib-compile-schemas``). The ``~/.cache`` compile path is only a
    convenience for running from a source checkout.
    """
    try:
        source = Gio.SettingsSchemaSource.get_default()
        if source is not None and source.lookup(APP_ID, True) is not None:
            return Gio.Settings.new(APP_ID)
    except Exception:
        pass

    # Development only: compile schemas from ./data into a user cache dir.
    if os.environ.get("TODO_SKIP_SCHEMA_CACHE") == "1":
        return None

    schema_dir = _project_schema_dir()
    if schema_dir is None:
        return None

    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache = cache_root / APP_ID / "schemas"
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    try:
        shutil.copy2(schema_dir / f"{APP_ID}.gschema.xml", cache / f"{APP_ID}.gschema.xml")
        subprocess.run(
            ["glib-compile-schemas", str(cache)],
            check=False,
            capture_output=True,
        )
        compiled = Gio.SettingsSchemaSource.new_from_directory(
            str(cache),
            Gio.SettingsSchemaSource.get_default(),
            False,
        )
        schema = compiled.lookup(APP_ID, False)
        if schema is None:
            return None
        return Gio.Settings.new_full(schema, None, None)
    except Exception:
        # Unwritable cache, missing glib-compile-schemas, etc. — app still runs.
        return None
