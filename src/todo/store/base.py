# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared store utilities: observable base and atomic JSON writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


class Observable:
    """Simple subscriber list used by TodoStore and PlannerStore."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()


def atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON atomically (temp file in same dir + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json(path: Path, default: Any) -> Any:
    """Read JSON from path, or return default if missing/corrupt."""
    data, _ok = read_json_with_status(path, default)
    return data


def read_json_with_status(path: Path, default: Any) -> tuple[Any, bool]:
    """Return (payload, ok). ok is False when the file existed but was unreadable."""
    if not path.exists():
        return default, True
    try:
        return json.loads(path.read_text(encoding="utf-8")), True
    except (OSError, json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return default, False
