"""Full-database export/import for the portable encrypted backup feature.

Design notes
------------
Every column encrypted with the *master key* (username, server system_id,
server salt, secret name/value, host/domain name, IP addresses) is decrypted
to plaintext on export and re-encrypted on import. This is deliberate: a
backup is meant to be restorable on a brand-new server with its *own*,
independently-generated master key, so anything tied to this server's master
key has to cross the export/import boundary as plaintext, protected instead
by the backup file's own encryption (BIP-39 seed + passphrase, applied
client-side in the browser -- see the web UI's backup module).

`otp_seed_enc` (a user's TOTP seed, encrypted with a key derived from their
*login password*) is the one exception: it is copied through unchanged. It
never depended on this server's master key, so it doesn't need decrypting --
and the whole point of a restore is that a user's existing username+password+
OTP combination keeps working on the new server without re-enrollment.

ACL entries are exported/imported by stable natural keys (system_id,
secret_name) rather than the numeric row ids, since those ids are
regenerated on import.

What's deliberately NOT included: `pending_enrollments` (transient
operational state, not data worth restoring) and `event_log` (an audit trail
of what happened on *this* server; restoring it onto a different server would
misrepresent its history). Both start empty on a freshly migrated database.

This module only ever produces/consumes a Python dict. Nothing here touches
the filesystem or knows about BIP-39/AES -- that all happens client-side in
the browser. The plaintext dict leaves this process exactly once, as an
HTTPS response body to an already-authenticated admin's own browser, and is
never written to disk server-side.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import blind_index, decrypt_field, encrypt_field
from app.models import AppServer, AppServerIp, Secret, SecretAcl, SystemConfig, User

BACKUP_FORMAT_VERSION = 1


async def export_database(session: AsyncSession) -> dict:
    mk = settings.master_key

    config_row = (await session.execute(select(SystemConfig).limit(1))).scalar_one_or_none()
    system_config = None
    if config_row is not None:
        system_config = {
            "host_name": decrypt_field(mk, "hostname", config_row.host_name_enc),
            "domain_name": decrypt_field(mk, "domain", config_row.domain_name_enc),
            "schema_version": config_row.schema_version,
        }

    users = [
        {
            "username": decrypt_field(mk, "username", user.username_enc),
            "otp_seed_enc": user.otp_seed_enc,  # opaque, password-derived; copied as-is
            "role": user.role,
            "must_change_password": user.must_change_password,
            "is_active": user.is_active,
            "active_until": user.active_until.isoformat(),
        }
        for user in (await session.execute(select(User))).scalars()
    ]

    servers = []
    server_id_to_system_id: dict[int, str] = {}
    for server in (await session.execute(select(AppServer))).scalars():
        system_id = decrypt_field(mk, "system_id", server.server_name_enc)
        server_id_to_system_id[server.id] = system_id
        ip_rows = (
            await session.execute(select(AppServerIp).where(AppServerIp.server_id == server.id))
        ).scalars()
        servers.append(
            {
                "system_id": system_id,
                "label": server.label,
                "server_salt": decrypt_field(mk, "server_salt", server.server_salt_enc),
                "is_active": server.is_active,
                "active_until": server.active_until.isoformat(),
                "ip_addresses": [
                    decrypt_field(mk, "ip_address", ip.ip_address_enc) for ip in ip_rows if ip.is_active
                ],
            }
        )

    secrets = []
    secret_id_to_name: dict[int, str] = {}
    for secret in (await session.execute(select(Secret))).scalars():
        name = decrypt_field(mk, "secret_name", secret.secret_name_enc)
        secret_id_to_name[secret.id] = name
        secrets.append(
            {
                "name": name,
                "value": decrypt_field(mk, "secret_value", secret.secret_value_enc),
                "is_active": secret.is_active,
            }
        )

    acl = [
        {
            "system_id": server_id_to_system_id[entry.server_id],
            "secret_name": secret_id_to_name[entry.secret_id],
            "is_active": entry.is_active,
        }
        for entry in (await session.execute(select(SecretAcl))).scalars()
        if entry.server_id in server_id_to_system_id and entry.secret_id in secret_id_to_name
    ]

    return {
        "format_version": BACKUP_FORMAT_VERSION,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "system_config": system_config,
        "users": users,
        "app_servers": servers,
        "secrets": secrets,
        "secret_acl": acl,
    }


async def wipe_database(session: AsyncSession) -> None:
    """Deletes all rows from every table this export/import cares about.
    Only ever called against a freshly-migrated, otherwise-empty database as
    part of the guided restore flow -- never exposed as a general "wipe" API."""
    await session.execute(delete(SecretAcl))
    await session.execute(delete(AppServerIp))
    await session.execute(delete(AppServer))
    await session.execute(delete(Secret))
    await session.execute(delete(User))
    await session.execute(delete(SystemConfig))


async def import_database(session: AsyncSession, data: dict) -> None:
    mk = settings.master_key

    if data.get("format_version") != BACKUP_FORMAT_VERSION:
        raise ValueError(f"unsupported backup format version: {data.get('format_version')!r}")

    if data.get("system_config"):
        cfg = data["system_config"]
        session.add(
            SystemConfig(
                host_name_enc=encrypt_field(mk, "hostname", cfg["host_name"]),
                domain_name_enc=encrypt_field(mk, "domain", cfg["domain_name"]),
                schema_version=cfg["schema_version"],
            )
        )

    for user in data.get("users", []):
        session.add(
            User(
                username_enc=encrypt_field(mk, "username", user["username"]),
                username_index=blind_index(mk, "username", user["username"]),
                otp_seed_enc=user["otp_seed_enc"],
                role=user["role"],
                must_change_password=user["must_change_password"],
                is_active=user["is_active"],
                active_until=dt.datetime.fromisoformat(user["active_until"]),
            )
        )

    secret_name_to_id: dict[str, int] = {}
    for secret in data.get("secrets", []):
        new_secret = Secret(
            secret_name_enc=encrypt_field(mk, "secret_name", secret["name"]),
            secret_name_index=blind_index(mk, "secret_name", secret["name"]),
            secret_value_enc=encrypt_field(mk, "secret_value", secret["value"]),
            is_active=secret["is_active"],
        )
        session.add(new_secret)
        await session.flush()
        secret_name_to_id[secret["name"]] = new_secret.id

    system_id_to_server_id: dict[str, int] = {}
    for server in data.get("app_servers", []):
        new_server = AppServer(
            server_name_enc=encrypt_field(mk, "system_id", server["system_id"]),
            server_name_index=blind_index(mk, "system_id", server["system_id"]),
            server_salt_enc=encrypt_field(mk, "server_salt", server["server_salt"]),
            label=server["label"],
            is_active=server["is_active"],
            active_until=dt.datetime.fromisoformat(server["active_until"]),
        )
        session.add(new_server)
        await session.flush()
        system_id_to_server_id[server["system_id"]] = new_server.id
        for ip in server["ip_addresses"]:
            session.add(
                AppServerIp(
                    server_id=new_server.id,
                    ip_address_enc=encrypt_field(mk, "ip_address", ip),
                    ip_address_index=blind_index(mk, "ip_address", ip),
                )
            )

    for entry in data.get("secret_acl", []):
        server_id = system_id_to_server_id.get(entry["system_id"])
        secret_id = secret_name_to_id.get(entry["secret_name"])
        if server_id is None or secret_id is None:
            continue
        session.add(SecretAcl(server_id=server_id, secret_id=secret_id, is_active=entry["is_active"]))
