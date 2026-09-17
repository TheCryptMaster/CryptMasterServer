"""Authentication flows.

Two separate flows, both parameterized-query only (no f-string SQL, unlike
v1's crypt_keeper.py / server_auth.py):

  1. Human admin login: username + password + TOTP. Password decrypts the
     user's TOTP seed (via app.password_crypto); TOTP is then checked.
  2. App-server challenge/response: server proves knowledge of its enrollment
     salt by Argon2-hashing (nonce + salt) after the vault hands it a nonce.
     Nonce state now lives in Redis with a TTL and is single-use, instead of
     an unbounded in-process list.
"""
from __future__ import annotations

import datetime as dt
import os

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import DecryptionError, blind_index, decrypt_field, encrypt_field
from app.models import AppServer, Secret, SecretAcl, User
from app.password_crypto import decrypt_with_password
from app.security import pop_pending_challenge, store_pending_challenge

_ph = PasswordHasher()


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def authenticate_user(
    session: AsyncSession, username: str, password: str, otp: str
) -> dt.datetime:
    """Returns the session's active-until timestamp, or raises AuthError."""
    username_index = blind_index(settings.master_key, "username", username)
    result = await session.execute(
        select(User).where(User.username_index == username_index, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("User not found")
    if user.active_until < dt.datetime.now(dt.timezone.utc):
        raise AuthError("User account expired")

    try:
        seed = decrypt_with_password(password, user.otp_seed_enc)
    except DecryptionError as exc:
        raise AuthError("Bad password") from exc

    totp = pyotp.TOTP(seed)
    if not totp.verify(otp=otp, valid_window=settings.totp_window):
        raise AuthError("Invalid OTP")

    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.api_open_minutes)


async def initiate_server_auth(
    session: AsyncSession, system_id: str, ip_address: str
) -> tuple[bool, str | None]:
    """Looks up an enrolled server and issues a single-use nonce.

    The pending challenge is keyed by the server's own identity (not by the
    nonce value), since the client never re-sends the nonce on the follow-up
    /get_secret call -- it only sends the Argon2 proof. Keying by identity
    also means a fresh /start_auth call naturally invalidates any nonce that
    was issued to that same server previously.

    Returns (allowed, nonce). On failure returns (False, None) without
    revealing *why* the lookup failed (unknown server vs. IP mismatch look
    identical to a caller, same as v1's intent).
    """
    system_id_index = blind_index(settings.master_key, "system_id", system_id)
    ip_index = blind_index(settings.master_key, "ip_address", ip_address)
    result = await session.execute(
        select(AppServer).where(
            AppServer.server_name_index == system_id_index,
            AppServer.ip_address_index == ip_index,
            AppServer.is_active.is_(True),
        )
    )
    server = result.scalar_one_or_none()
    if server is None:
        return False, None

    server_salt = decrypt_field(settings.master_key, "server_salt", server.server_salt_enc)
    nonce = os.urandom(24).hex()
    expected_plaintext = nonce + server_salt
    await store_pending_challenge(system_id_index, expected_plaintext)
    return True, nonce


async def validate_server_secret(system_id: str, provided_secret: str | None) -> bool:
    if not provided_secret or not system_id:
        return False
    system_id_index = blind_index(settings.master_key, "system_id", system_id)
    expected_plaintext = await pop_pending_challenge(system_id_index)
    if expected_plaintext is None:
        return False
    try:
        return _ph.verify(provided_secret, expected_plaintext)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash string, etc.
        return False


async def get_secret_for_server(
    session: AsyncSession, system_id: str, ip_address: str, requested_secret_name: str
) -> str | None:
    """Looks up a secret, enforcing the server<->secret ACL.

    v1 defined `secret_acl` in its schema but never checked it here -- any
    enrolled server could fetch any secret by name. This joins through the
    ACL table before returning anything.
    """
    system_id_index = blind_index(settings.master_key, "system_id", system_id)
    ip_index = blind_index(settings.master_key, "ip_address", ip_address)
    secret_index = blind_index(settings.master_key, "secret_name", requested_secret_name)

    result = await session.execute(
        select(Secret.secret_value_enc)
        .join(SecretAcl, SecretAcl.secret_id == Secret.id)
        .join(AppServer, AppServer.id == SecretAcl.server_id)
        .where(
            AppServer.server_name_index == system_id_index,
            AppServer.ip_address_index == ip_index,
            AppServer.is_active.is_(True),
            SecretAcl.is_active.is_(True),
            Secret.secret_name_index == secret_index,
            Secret.is_active.is_(True),
        )
    )
    encrypted = result.scalar_one_or_none()
    if encrypted is None:
        return None
    return decrypt_field(settings.master_key, "secret_value", encrypted)
