"""First-run bootstrap: default admin credentials for a net-new server.

These are intentionally public (documented in the README) -- the security
boundary is the *mandatory* password change and OTP enrollment on first
login (see routers/auth.py:change_password), not secrecy of this constant.
A server that's been sitting reachable with these still active is a
configuration error, not a leaked secret.
"""
from __future__ import annotations

import datetime as dt

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import blind_index, encrypt_field
from app.models import User
from app.password_crypto import encrypt_with_password

DEFAULT_ADMIN_USERNAME = "admin@cryptmaster.local"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"


async def create_default_admin(session: AsyncSession) -> None:
    throwaway_seed = pyotp.random_base32()
    session.add(
        User(
            username_enc=encrypt_field(settings.master_key, "username", DEFAULT_ADMIN_USERNAME),
            username_index=blind_index(settings.master_key, "username", DEFAULT_ADMIN_USERNAME),
            otp_seed_enc=encrypt_with_password(DEFAULT_ADMIN_PASSWORD, throwaway_seed),
            role="admin",
            must_change_password=True,
            active_until=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3650),
        )
    )
