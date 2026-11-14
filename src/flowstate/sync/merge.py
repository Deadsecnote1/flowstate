# SPDX-License-Identifier: GPL-3.0-or-later
"""Conflict helpers for applying remote rows."""

from __future__ import annotations

from flowstate.sync.timeutil import parse_iso


def remote_is_newer(local_client_updated_at: str, remote_row: dict) -> bool:
    remote_client = parse_iso(str(remote_row.get("client_updated_at", "")))
    local_client = parse_iso(local_client_updated_at)
    if remote_client is None:
        return True
    if local_client is None:
        return True
    return remote_client >= local_client
