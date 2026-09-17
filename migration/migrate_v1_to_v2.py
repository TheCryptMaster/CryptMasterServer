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

This CLI and the web admin console's "migrate from a legacy server" first-run
option (app/web/routers/setup.py) share the same read path
(migration/legacy_reader.py) and write path (migration/writer.py); this file
is just the argument parsing and reporting layer on top of both.

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
from dataclasses import dataclass, field

import sqlalchemy as sa

from app.db import session_scope
from migration.legacy_reader import LegacyDecryptionError, read_app_server, read_secret, read_system_config, read_user
from migration.writer import write_app_server, write_secret, write_system_config, write_user


@dataclass
class MigrationCounts:
    secrets: int = 0
    app_servers: int = 0
    users: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def load_old_entropy(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


async def run_migration(
    old_dsn: str,
    entropy: str,
    secrets: list[str],
    app_servers: list[dict],
    users: list[dict],
    dry_run: bool = False,
) -> MigrationCounts:
    """The full migration, driven from already-loaded inputs (no file I/O,
    no argparse) so it can be awaited directly from a FastAPI request
    handler as well as from main() below."""
    counts = MigrationCounts()
    old_engine = sa.create_engine(old_dsn)

    try:
        with old_engine.connect() as old_conn:
            config = read_system_config(old_conn, entropy)
            if config is not None:
                if dry_run:
                    counts.errors.append(f"[system_config] would migrate host={config['host_name']!r} domain={config['domain_name']!r}")
                else:
                    async with session_scope() as session:
                        wrote = await write_system_config(session, config["host_name"], config["domain_name"])
                    counts.errors.append("[system_config] migrated" if wrote else "[system_config] already present, skipped")

            for name in secrets:
                value = read_secret(old_conn, entropy, name)
                if value is None:
                    counts.failed += 1
                    counts.errors.append(f"[secret:{name}] not found in old database")
                    continue
                if dry_run:
                    counts.secrets += 1
                    continue
                async with session_scope() as session:
                    wrote = await write_secret(session, name, value)
                if wrote:
                    counts.secrets += 1
                else:
                    counts.skipped += 1
                    counts.errors.append(f"[secret:{name}] already present in new database, skipped")

            for entry in app_servers:
                system_id, ip_address = entry["system_id"], entry["ip_address"]
                salt = read_app_server(old_conn, entropy, system_id, ip_address)
                if salt is None:
                    counts.failed += 1
                    counts.errors.append(f"[server:{system_id}] not found in old database for ip {ip_address}")
                    continue
                if dry_run:
                    counts.app_servers += 1
                    continue
                async with session_scope() as session:
                    wrote = await write_app_server(session, system_id, salt, ip_address)
                if wrote:
                    counts.app_servers += 1
                else:
                    counts.skipped += 1
                    counts.errors.append(f"[server:{system_id}] already present in new database, skipped")

            for entry in users:
                email, password = entry["email"].lower(), entry["password"]
                try:
                    result = read_user(old_conn, entropy, email, password)
                except LegacyDecryptionError:
                    counts.failed += 1
                    counts.errors.append(f"[user:{email}] found but the supplied password did not decrypt their OTP seed")
                    continue
                if result is None:
                    counts.failed += 1
                    counts.errors.append(f"[user:{email}] not found (or inactive) in old database")
                    continue
                seed, active_until = result
                if dry_run:
                    counts.users += 1
                    continue
                async with session_scope() as session:
                    wrote = await write_user(session, email, password, seed, active_until)
                if wrote:
                    counts.users += 1
                else:
                    counts.skipped += 1
                    counts.errors.append(f"[user:{email}] already present in new database, skipped")
    finally:
        old_engine.dispose()

    return counts


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
    counts = asyncio.run(
        run_migration(
            args.old_dsn,
            entropy,
            manifest.get("secrets", []),
            manifest.get("app_servers", []),
            manifest.get("users", []),
            dry_run=args.dry_run,
        )
    )

    for line in counts.errors:
        print(line)

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
