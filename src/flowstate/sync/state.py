# SPDX-License-Identifier: GPL-3.0-or-later
"""Persist Supabase session and sync cursor on disk."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from flowstate.settings import APP_ID
from flowstate.store.base import atomic_write_json, read_json, resolve_data_dir


@dataclass
class SyncSession:
    access_token: str
    refresh_token: str
    expires_at: int | None
    user_id: str
    email: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SyncSession | None:
        token = str(raw.get("access_token", "")).strip()
        refresh = str(raw.get("refresh_token", "")).strip()
        user_id = str(raw.get("user_id", "")).strip()
        if not token or not refresh or not user_id:
            return None
        expires = raw.get("expires_at")
        expires_at = int(expires) if expires is not None else None
        return cls(
            access_token=token,
            refresh_token=refresh,
            expires_at=expires_at,
            user_id=user_id,
            email=str(raw.get("email", "")).strip(),
        )


class SyncStateStore:
    """sync_state.json — session + last successful pull timestamp."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or resolve_data_dir(APP_ID)
        self._path = self._dir / "sync_state.json"
        self._session_path = self._dir / "sync_session.json"

    def load_last_sync_at(self) -> str | None:
        raw = read_json(self._path, {})
        value = raw.get("last_sync_at")
        return str(value) if value else None

    def save_last_sync_at(self, iso: str) -> None:
        raw = read_json(self._path, {})
        raw["last_sync_at"] = iso
        atomic_write_json(self._path, raw)

    def load_session(self) -> SyncSession | None:
        raw = read_json(self._session_path, {})
        if not raw:
            return None
        return SyncSession.from_dict(raw)

    def save_session(self, session: SyncSession) -> None:
        atomic_write_json(self._session_path, asdict(session))

    def clear_session(self) -> None:
        if self._session_path.exists():
            try:
                self._session_path.unlink()
            except OSError:
                pass

    def is_signed_in(self) -> bool:
        return self.load_session() is not None
