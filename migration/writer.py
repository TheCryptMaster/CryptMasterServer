"""Async, idempotent writes of already-decrypted plaintext into the current
(v2) database. Shared by the CLI migration tool and the web UI's "migrate
from a legacy server" first-run option -- neither one talks to the old
database directly through here; they call migration.legacy_reader first and
pass the plaintext result in.

Every function returns True if it wrote a new row, False if it skipped
because a matching row already existed (so re-running a migration is safe).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import blind_index, encrypt_field
from app.models import AppServer, AppServerIp, Secret, SystemConfig, User
from app.password_crypto import encrypt_with_password


async def write_system_config(session: AsyncSession, host_name: str, domain_name: str) -> bool:
    existing = await session.execute(select(SystemConfig).limit(1))
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(
        SystemConfig(
            host_name_enc=encrypt_field(settings.master_key, "hostname", host_name),
            domain_name_enc=encrypt_field(settings.master_key, "domain", domain_name),
            schema_version="2.0.0",
        )
    )
    return True


async def write_secret(session: AsyncSession, name: str, value: str) -> bool:
    index = blind_index(settings.master_key, "secret_name", name)
    existing = await session.execute(select(Secret.id).where(Secret.secret_name_index == index))
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(
        Secret(
            secret_name_enc=encrypt_field(settings.master_key, "secret_name", name),
            secret_name_index=index,
            secret_value_enc=encrypt_field(settings.master_key, "secret_value", value),
        )
    )
    return True


async def write_app_server(session: AsyncSession, system_id: str, salt: str, ip_address: str) -> bool:
    index = blind_index(settings.master_key, "system_id", system_id)
    existing = await session.execute(select(AppServer.id).where(AppServer.server_name_index == index))
    if existing.scalar_one_or_none() is not None:
        return False
    new_server = AppServer(
        server_name_enc=encrypt_field(settings.master_key, "system_id", system_id),
        server_name_index=index,
        server_salt_enc=encrypt_field(settings.master_key, "server_salt", salt),
        active_until=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=60),
    )
    session.add(new_server)
    await session.flush()
    session.add(
        AppServerIp(
            server_id=new_server.id,
            ip_address_enc=encrypt_field(settings.master_key, "ip_address", ip_address),
            ip_address_index=blind_index(settings.master_key, "ip_address", ip_address),
        )
    )
    return True


async def write_user(
    session: AsyncSession, email: str, password: str, seed: str, active_until: dt.datetime, role: str = "admin"
) -> bool:
    """role defaults to "admin": v1 had no role concept -- every user who
    could open the vault had full authority over it, so a migrated user
    keeps that same standing in v2 rather than being downgraded to
    "operator" by the model's normal default."""
    index = blind_index(settings.master_key, "username", email)
    existing = await session.execute(select(User.id).where(User.username_index == index))
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(
        User(
            username_enc=encrypt_field(settings.master_key, "username", email),
            username_index=index,
            otp_seed_enc=encrypt_with_password(password, seed),
            role=role,
            active_until=active_until,
        )
    )
    return True
