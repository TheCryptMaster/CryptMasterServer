"""Browser session management for the admin web UI.

Separate from the server-to-server API's nonce/challenge auth in app.auth --
this is plain cookie-based session auth for humans using the React admin
console. Sessions are opaque random tokens, stored server-side in Redis with
a TTL (never a self-contained JWT, so a session can be revoked instantly by
deleting its Redis key -- e.g. on logout or role change).
"""
from __future__ import annotations

import json
import secrets as pysecrets

import redis.asyncio as redis

from app.config import settings

_redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

SESSION_COOKIE_NAME = "cm_session"
SESSION_TTL_SECONDS = 8 * 60 * 60  # 8 hours


class SessionData:
    def __init__(self, user_id: int, role: str, must_change_password: bool):
        self.user_id = user_id
        self.role = role
        self.must_change_password = must_change_password

    def to_json(self) -> str:
        return json.dumps(
            {"user_id": self.user_id, "role": self.role, "must_change_password": self.must_change_password}
        )

    @classmethod
    def from_json(cls, raw: str) -> "SessionData":
        data = json.loads(raw)
        return cls(data["user_id"], data["role"], data["must_change_password"])


async def create_session(user_id: int, role: str, must_change_password: bool) -> str:
    token = pysecrets.token_urlsafe(32)
    session = SessionData(user_id, role, must_change_password)
    await _redis.set(f"cryptmaster:websession:{token}", session.to_json(), ex=SESSION_TTL_SECONDS)
    return token


async def get_session(token: str | None) -> SessionData | None:
    if not token:
        return None
    raw = await _redis.get(f"cryptmaster:websession:{token}")
    if raw is None:
        return None
    return SessionData.from_json(raw)


async def refresh_session(token: str, session: SessionData) -> None:
    """Called after a session's underlying user record changes (password
    change, role change) so the cached session reflects it immediately."""
    await _redis.set(f"cryptmaster:websession:{token}", session.to_json(), ex=SESSION_TTL_SECONDS)


async def destroy_session(token: str) -> None:
    await _redis.delete(f"cryptmaster:websession:{token}")
