#!/usr/bin/env python3
"""Migrate a v1 Crypt Master database into a fresh v2 database.

WHY THIS NEEDS A MANIFEST, NOT JUST A DB CONNECTION
----------------------------------------------------
v1 did not store secret names, server system_ids, or IP addresses as
reversible ciphertext. It stored them as `generate_secret(value)` -- a
one-way, PRNG-derived hash used purely as a lookup key (functionally a blind
index, just without calling it that). That means:

  * `secrets.secret_name`      -> one-way hash of the secret's name
  * `app_servers.server_name`  -> one-way hash of the system_id
  * `app_servers.ip_address`   -> one-way hash of the IP

None of those can be inverted back to the original string. The *values*
behind them (`secrets.secret_pass`, `app_servers.server_salt`) ARE genuinely
encrypted and can be recovered -- but only once you already know the
original name/system_id/ip to re-derive the same hash and find the row.

In practice this was never a problem operationally: every caller of the old
API already had to know the secret name / its own system_id up front to ask
for it. This tool asks the same of you: give it the list of secret names and
(system_id, ip_address) pairs you know are in the old database, and it will
look each one up, decrypt it, and re-insert it into the new database under
the new (actually-random-salted) encryption scheme.

USER ACCOUNTS are handled separately: a user's TOTP seed was encrypted with
a key derived from *their login password*, which was never stored anywhere,
by design. There is no way to migrate a user's OTP seed without that
password. You can supply passwords transiently in the manifest for a
scripted cutover window, but the recommended path is simply to re-enroll
each user (`python -m cli.manage`, option "Add user") -- it's one QR code
scan and takes under a minute per person, and it means every user starts
the new system on the stronger Argon2id-derived key by default.

USAGE
-----
    python -m migration.migrate_v1_to_v2 \\
        --old-dsn postgresql://cryptmaster:oldpass@old-host:5432/cryptmaster_db \\
        --old-entropy-file /path/to/.entropy \\
        --manifest manifest.json \\
        [--dry-run]

manifest.json:
{
  "secrets": ["stripe_api_key", "db_backup_password"],
  "app_servers": [{"system_id": "<hex md5 from the client>", "ip_address": "10.0.0.5"}],
  "users": [{"email": "admin@example.com", "password": "<current password>"}]
}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from app.config import settings
from app.crypto import blind_index, encrypt_field
from app.db import session_scope
from app.models import AppServer, AppServerIp, Secret, SystemConfig, User
from app.password_crypto import encrypt_with_password
from migration.legacy_crypto import legacy_decrypt_secret, legacy_generate_secret


@dataclass
class MigrationCounts:
    secrets: int = 0
    app_servers: int = 0
    users: int = 0
    skipped: int = 0
    failed: int = 0


def load_old_entropy(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def old_engine(dsn: str) -> sa.Engine:
    return sa.create_engine(dsn)


def migrate_system_config(old_conn: sa.Connection, entropy: str, dry_run: bool) -> None:
    row = old_conn.execute(
        sa.text("SELECT domain_name, host_name FROM cryptmaster_warden ORDER BY id ASC LIMIT 1")
    ).mappings().first()
    if row is None:
        print("[system_config] no cryptmaster_warden row found in old DB, skipping")
        return
    domain = legacy_decrypt_secret(legacy_generate_secret(entropy, "domain"), row["domain_name"])
    host = legacy_decrypt_secret(legacy_generate_secret(entropy, "hostname"), row["host_name"])
    print(f"[system_config] recovered host={host!r} domain={domain!r}")
    if dry_run:
        return

    async def _write():
        async with session_scope() as session:
            existing = await session.execute(sa.select(SystemConfig).limit(1))
            if existing.scalar_one_or_none() is not None:
                print("[system_config] a config row already exists in the new DB, leaving it alone")
                return
            session.add(
                SystemConfig(
                    host_name_enc=encrypt_field(settings.master_key, "hostname", host),
                    domain_name_enc=encrypt_field(settings.master_key, "domain", domain),
                    schema_version="2.0.0",
                )
            )

    asyncio.run(_write())


def migrate_secrets(old_conn: sa.Connection, entropy: str, names: list[str], dry_run: bool, counts: MigrationCounts) -> None:
    for name in names:
        legacy_name_hash = legacy_generate_secret(entropy, name)
        row = old_conn.execute(
            sa.text("SELECT secret_pass FROM secrets WHERE secret_name = :name"),
            {"name": legacy_name_hash},
        ).mappings().first()
        if row is None:
            print(f"[secret:{name}] not found in old DB")
            counts.failed += 1
            continue
        try:
            value = legacy_decrypt_secret(legacy_generate_secret(entropy, legacy_name_hash), row["secret_pass"])
        except Exception as exc:  # noqa: BLE001
            print(f"[secret:{name}] failed to decrypt: {exc}")
            counts.failed += 1
            continue
        print(f"[secret:{name}] recovered ({len(value)} chars)")
        if dry_run:
            counts.secrets += 1
            continue

        async def _write(name=name, value=value):
            async with session_scope() as session:
                index = blind_index(settings.master_key, "secret_name", name)
                existing = await session.execute(select_secret_by_index(index))
                if existing.scalar_one_or_none() is not None:
                    print(f"[secret:{name}] already present in new DB, skipping")
                    counts.skipped += 1
                    return
                session.add(
                    Secret(
                        secret_name_enc=encrypt_field(settings.master_key, "secret_name", name),
                        secret_name_index=index,
                        secret_value_enc=encrypt_field(settings.master_key, "secret_value", value),
                    )
                )
                counts.secrets += 1

        asyncio.run(_write())


def select_secret_by_index(index: str):
    return sa.select(Secret.id).where(Secret.secret_name_index == index)


def migrate_app_servers(
    old_conn: sa.Connection, entropy: str, servers: list[dict], dry_run: bool, counts: MigrationCounts
) -> None:
    for entry in servers:
        system_id, ip_address = entry["system_id"], entry["ip_address"]
        legacy_id_hash = legacy_generate_secret(entropy, str(system_id))
        legacy_ip_hash = legacy_generate_secret(entropy, ip_address)
        row = old_conn.execute(
            sa.text(
                "SELECT server_salt FROM app_servers WHERE server_name = :sid AND ip_address = :ip"
            ),
            {"sid": legacy_id_hash, "ip": legacy_ip_hash},
        ).mappings().first()
        if row is None:
            print(f"[server:{system_id}] not found in old DB for ip {ip_address}")
            counts.failed += 1
            continue
        try:
            salt = legacy_decrypt_secret(legacy_generate_secret(entropy, "system_salt"), row["server_salt"])
        except Exception as exc:  # noqa: BLE001
            print(f"[server:{system_id}] failed to decrypt salt: {exc}")
            counts.failed += 1
            continue
        print(f"[server:{system_id}] recovered salt")
        if dry_run:
            counts.app_servers += 1
            continue

        async def _write(system_id=system_id, ip_address=ip_address, salt=salt):
            async with session_scope() as session:
                index = blind_index(settings.master_key, "system_id", system_id)
                existing = await session.execute(
                    sa.select(AppServer.id).where(AppServer.server_name_index == index)
                )
                if existing.scalar_one_or_none() is not None:
                    print(f"[server:{system_id}] already present in new DB, skipping")
                    counts.skipped += 1
                    return
                new_server = AppServer(
                    server_name_enc=encrypt_field(settings.master_key, "system_id", system_id),
                    server_name_index=index,
                    server_salt_enc=encrypt_field(settings.master_key, "server_salt", salt),
                    active_until=datetime.now(timezone.utc) + timedelta(days=60),
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
                counts.app_servers += 1

        asyncio.run(_write())


def migrate_users(
    old_conn: sa.Connection, entropy: str, users: list[dict], dry_run: bool, counts: MigrationCounts
) -> None:
    for entry in users:
        email, password = entry["email"].lower(), entry["password"]
        legacy_username_hash = legacy_generate_secret(entropy, email)
        row = old_conn.execute(
            sa.text(
                "SELECT id, user_otp_hash, active_until FROM user_accounts WHERE username = :u AND is_active = True"
            ),
            {"u": legacy_username_hash},
        ).mappings().first()
        if row is None:
            print(f"[user:{email}] not found (or inactive) in old DB")
            counts.failed += 1
            continue
        try:
            legacy_password_key = legacy_generate_secret(entropy, password)
            seed = legacy_decrypt_secret(legacy_password_key, row["user_otp_hash"])
        except Exception as exc:  # noqa: BLE001
            print(f"[user:{email}] failed to decrypt OTP seed (wrong password?): {exc}")
            counts.failed += 1
            continue
        print(f"[user:{email}] recovered OTP seed")
        if dry_run:
            counts.users += 1
            continue

        async def _write(email=email, password=password, seed=seed, active_until=row["active_until"]):
            async with session_scope() as session:
                index = blind_index(settings.master_key, "username", email)
                existing = await session.execute(sa.select(User.id).where(User.username_index == index))
                if existing.scalar_one_or_none() is not None:
                    print(f"[user:{email}] already present in new DB, skipping")
                    counts.skipped += 1
                    return
                session.add(
                    User(
                        username_enc=encrypt_field(settings.master_key, "username", email),
                        username_index=index,
                        otp_seed_enc=encrypt_with_password(password, seed),
                        active_until=active_until,
                    )
                )
                counts.users += 1

        asyncio.run(_write())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old-dsn", required=True, help="SQLAlchemy DSN for the OLD v1 database")
    parser.add_argument("--old-entropy-file", required=True, help="Path to the old .entropy file")
    parser.add_argument("--manifest", required=True, help="Path to a manifest.json (see module docstring)")
    parser.add_argument("--dry-run", action="store_true", help="Decrypt and report, but write nothing")
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    entropy = load_old_entropy(args.old_entropy_file)
    engine = old_engine(args.old_dsn)
    counts = MigrationCounts()

    with engine.connect() as old_conn:
        migrate_system_config(old_conn, entropy, args.dry_run)
        migrate_secrets(old_conn, entropy, manifest.get("secrets", []), args.dry_run, counts)
        migrate_app_servers(old_conn, entropy, manifest.get("app_servers", []), args.dry_run, counts)
        migrate_users(old_conn, entropy, manifest.get("users", []), args.dry_run, counts)

    mode = "DRY RUN -- " if args.dry_run else ""
    print(
        f"\n{mode}Done. secrets={counts.secrets} app_servers={counts.app_servers} "
        f"users={counts.users} skipped={counts.skipped} failed={counts.failed}"
    )
    if manifest.get("users"):
        print(
            "\nNote: any users NOT listed in the manifest were not migrated. "
            "Re-enroll them with `python -m cli.manage` instead of chasing down their old password."
        )
    if counts.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
