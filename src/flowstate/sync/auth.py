# SPDX-License-Identifier: GPL-3.0-or-later
"""Google sign-in via Supabase OAuth and local loopback redirect (Linux GTK)."""

from __future__ import annotations

import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Callable

from flowstate.sync.client import SyncClient, SyncClientError, supabase_available
from flowstate.sync.config import load_sync_config
from flowstate.sync.state import SyncSession, SyncStateStore


class AuthError(Exception):
    pass


class _LoopbackServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


OAUTH_LOOPBACK_PORT = 8765


def _loopback_redirect_uri() -> str:
    return f"http://127.0.0.1:{OAUTH_LOOPBACK_PORT}/callback"


def sign_in_with_google(on_progress: Callable[[str], None] | None = None) -> SyncSession:
    """Open browser for Google OAuth; return persisted session on success."""
    if not supabase_available():
        raise AuthError(
            "Install sync support: pip install --user -r requirements-sync.txt"
        )
    config = load_sync_config()
    if config is None:
        raise AuthError(
            "Supabase not configured. Copy config/sync.env.example to "
            "~/.config/io.github.Deadsecnote1.Flowstate/sync.env"
        )

    port = OAUTH_LOOPBACK_PORT
    redirect_uri = _loopback_redirect_uri()
    result: dict[str, str | SyncSession | AuthError] = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args) -> None:
            return

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = urllib.parse.parse_qs(parsed.query)
            if "error" in params:
                result["error"] = AuthError(params["error"][0])
                self._ok_page("Sign-in failed. You can close this tab.")
                done.set()
                return
            code = (params.get("code") or [None])[0]
            if not code:
                result["error"] = AuthError("Missing authorization code")
                self._ok_page("Sign-in failed. You can close this tab.")
                done.set()
                return
            result["code"] = code
            self._ok_page("Signed in to Flowstate. You can close this tab.")
            done.set()

        def _ok_page(self, message: str) -> None:
            body = f"<html><body><p>{message}</p></body></html>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    if on_progress:
        on_progress("Opening browser for Google sign-in…")

    client = SyncClient(config=config)
    oauth = client.raw.auth.sign_in_with_oauth(
        {
            "provider": "google",
            "options": {
                "redirect_to": redirect_uri,
                "skip_browser_redirect": True,
            },
        }
    )
    auth_url = getattr(oauth, "url", None)
    if auth_url is None and isinstance(oauth, dict):
        auth_url = oauth.get("url")
    if not auth_url:
        raise AuthError("Supabase did not return an OAuth URL")

    server = _LoopbackServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if not webbrowser.open(auth_url):
        server.shutdown()
        raise AuthError("Could not open a web browser for sign-in")

    if not done.wait(timeout=300):
        server.shutdown()
        raise AuthError("Sign-in timed out")

    server.shutdown()

    if "error" in result:
        raise result["error"]  # type: ignore[misc]

    code = result.get("code")
    if not isinstance(code, str):
        raise AuthError("Sign-in was cancelled")

    if on_progress:
        on_progress("Completing sign-in…")

    auth_response = client.raw.auth.exchange_code_for_session(
        {"auth_code": code, "redirect_to": redirect_uri}
    )
    session_data = auth_response.session
    user = auth_response.user
    if session_data is None or user is None:
        raise AuthError("Supabase returned an empty session")

    sync_session = SyncSession(
        access_token=session_data.access_token,
        refresh_token=session_data.refresh_token,
        expires_at=session_data.expires_at,
        user_id=str(user.id),
        email=str(getattr(user, "email", "") or ""),
    )
    state = SyncStateStore()
    state.save_session(sync_session)
    client.apply_session(sync_session)
    return sync_session


def sign_out() -> None:
    state = SyncStateStore()
    try:
        client = SyncClient()
        client.raw.auth.sign_out()
    except SyncClientError:
        pass
    state.clear_session()
