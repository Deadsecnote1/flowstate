# SPDX-License-Identifier: GPL-3.0-or-later
"""Supabase client wrapper with optional dependency."""

from __future__ import annotations

from typing import Any

from flowstate.sync.config import SyncConfig, load_sync_config
from flowstate.sync.state import SyncSession, SyncStateStore

try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional at runtime
    Client = Any  # type: ignore[misc, assignment]
    create_client = None  # type: ignore[assignment]
    SUPABASE_AVAILABLE = False


class SyncClientError(Exception):
    pass


class SyncClient:
    def __init__(
        self,
        config: SyncConfig | None = None,
        state: SyncStateStore | None = None,
    ) -> None:
        if not SUPABASE_AVAILABLE:
            raise SyncClientError(
                "supabase-py is not installed. Run: pip install --user -r requirements-sync.txt"
            )
        self._config = config or load_sync_config()
        if self._config is None:
            raise SyncClientError("Supabase is not configured")
        self._state = state or SyncStateStore()
        self._client: Client = create_client(self._config.url, self._config.anon_key)

    @property
    def raw(self) -> Client:
        return self._client

    def apply_session(self, session: SyncSession) -> None:
        self._client.auth.set_session(session.access_token, session.refresh_token)

    def restore_session(self) -> SyncSession | None:
        session = self._state.load_session()
        if session is None:
            return None
        try:
            self.apply_session(session)
            refreshed = self._client.auth.refresh_session()
            if refreshed.session is not None:
                user = refreshed.user
                session = SyncSession(
                    access_token=refreshed.session.access_token,
                    refresh_token=refreshed.session.refresh_token,
                    expires_at=refreshed.session.expires_at,
                    user_id=str(user.id) if user is not None else session.user_id,
                    email=str(getattr(user, "email", "") or session.email),
                )
                self._state.save_session(session)
            return session
        except Exception:
            self._state.clear_session()
            return None

    def upsert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self._client.table(table).upsert(rows).execute()

    def fetch_since(self, table: str, since_iso: str) -> list[dict[str, Any]]:
        response = (
            self._client.table(table)
            .select("*")
            .gt("server_updated_at", since_iso)
            .execute()
        )
        return list(response.data or [])


def supabase_available() -> bool:
    return SUPABASE_AVAILABLE
