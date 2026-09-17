"""Per-identity throttling and lockout state, backed by Redis.

v1 kept `fail_count` / `fail_disable` as plain module-level globals in
crypt_keeper.py: one shared counter for the entire process, across every
caller. Three bad requests from *anyone* locked out *everyone* for an hour,
and none of it survived a restart or worked across multiple workers.

Here every counter is keyed by identity (e.g. "login:<username_index>" or
"secret:<ip_address>") with a Redis TTL, so lockouts are scoped to the
identity that actually failed and survive process restarts / multiple
workers automatically.
"""
from __future__ import annotations

import redis.asyncio as redis

from app.config import settings

_redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


def _fail_key(scope: str, identity: str) -> str:
    return f"cryptmaster:fail:{scope}:{identity}"


def _lock_key(scope: str, identity: str) -> str:
    return f"cryptmaster:lock:{scope}:{identity}"


async def is_locked(scope: str, identity: str) -> bool:
    return bool(await _redis.get(_lock_key(scope, identity)))


async def record_failure(scope: str, identity: str) -> None:
    fail_key = _fail_key(scope, identity)
    count = await _redis.incr(fail_key)
    if count == 1:
        await _redis.expire(fail_key, settings.fail_lockout_minutes * 60)
    if count >= settings.fail_threshold:
        await _redis.set(_lock_key(scope, identity), "1", ex=settings.fail_lockout_minutes * 60)


async def clear_failures(scope: str, identity: str) -> None:
    await _redis.delete(_fail_key(scope, identity), _lock_key(scope, identity))


_SYSTEM_OPEN_KEY = "cryptmaster:system_open"


async def mark_system_open() -> str:
    """A successful admin TOTP login opens a system-wide window during which
    app servers may fetch secrets, for api_open_minutes. This mirrors v1's
    intent (an admin must physically "open" the vault) but as a Redis key
    with a TTL instead of a process-global `active_until` datetime, so it
    survives restarts and works with multiple workers."""
    import datetime as dt

    until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.api_open_minutes)
    await _redis.set(_SYSTEM_OPEN_KEY, "1", ex=settings.api_open_minutes * 60)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


async def is_system_open() -> bool:
    return bool(await _redis.get(_SYSTEM_OPEN_KEY))


async def store_pending_challenge(identity: str, expected_response: str, ttl_seconds: int = 120) -> None:
    """Keyed by the caller's identity (not the nonce) -- see app.auth for why."""
    await _redis.set(f"cryptmaster:challenge:{identity}", expected_response, ex=ttl_seconds)


async def pop_pending_challenge(identity: str) -> str | None:
    key = f"cryptmaster:challenge:{identity}"
    value = await _redis.get(key)
    if value is not None:
        await _redis.delete(key)
    return value
