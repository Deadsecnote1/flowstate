# SPDX-License-Identifier: GPL-3.0-or-later
"""UTC timestamp helpers for sync."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def delta_since(iso: str | None, buffer_seconds: int = 10) -> str:
    """Return ISO timestamp for pull queries (last sync minus safety buffer)."""
    if not iso:
        return "1970-01-01T00:00:00+00:00"
    dt = parse_iso(iso)
    if dt is None:
        return "1970-01-01T00:00:00+00:00"
    return (dt - timedelta(seconds=buffer_seconds)).isoformat()
