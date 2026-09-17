"""Pure, synchronous read+decrypt access to a v1 database.

Kept separate from any writing logic (see migration/writer.py) so both the
CLI tool (migrate_v1_to_v2.py) and the web UI's "migrate from a legacy
server" first-run option can share the exact same read path against the old
database, instead of drifting apart.

See migrate_v1_to_v2.py's module docstring for why secret names /
system_ids / IPs have to be supplied by the caller rather than discovered:
v1 stored them only as one-way hashes.
"""
from __future__ import annotations

import datetime as dt

import sqlalchemy as sa

from migration.legacy_crypto import legacy_decrypt_secret, legacy_generate_secret


class LegacyDecryptionError(Exception):
    """Row was found, but the supplied credential (password) didn't decrypt it."""


def read_system_config(old_conn: sa.Connection, entropy: str) -> dict | None:
    row = (
        old_conn.execute(sa.text("SELECT domain_name, host_name FROM cryptmaster_warden ORDER BY id ASC LIMIT 1"))
        .mappings()
        .first()
    )
    if row is None:
        return None
    return {
        "domain_name": legacy_decrypt_secret(legacy_generate_secret(entropy, "domain"), row["domain_name"]),
        "host_name": legacy_decrypt_secret(legacy_generate_secret(entropy, "hostname"), row["host_name"]),
    }


def read_secret(old_conn: sa.Connection, entropy: str, name: str) -> str | None:
    legacy_name_hash = legacy_generate_secret(entropy, name)
    row = (
        old_conn.execute(sa.text("SELECT secret_pass FROM secrets WHERE secret_name = :name"), {"name": legacy_name_hash})
        .mappings()
        .first()
    )
    if row is None:
        return None
    return legacy_decrypt_secret(legacy_generate_secret(entropy, legacy_name_hash), row["secret_pass"])


def read_app_server(old_conn: sa.Connection, entropy: str, system_id: str, ip_address: str) -> str | None:
    """Returns the server's enrollment salt, or None if not found."""
    legacy_id_hash = legacy_generate_secret(entropy, str(system_id))
    legacy_ip_hash = legacy_generate_secret(entropy, ip_address)
    row = (
        old_conn.execute(
            sa.text("SELECT server_salt FROM app_servers WHERE server_name = :sid AND ip_address = :ip"),
            {"sid": legacy_id_hash, "ip": legacy_ip_hash},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return legacy_decrypt_secret(legacy_generate_secret(entropy, "system_salt"), row["server_salt"])


def read_user(
    old_conn: sa.Connection, entropy: str, email: str, password: str
) -> tuple[str, dt.datetime] | None:
    """Returns (otp_seed, active_until), or None if the user isn't found (or
    is inactive). Raises LegacyDecryptionError if found but `password` is
    wrong."""
    legacy_username_hash = legacy_generate_secret(entropy, email)
    row = (
        old_conn.execute(
            sa.text(
                "SELECT user_otp_hash, active_until FROM user_accounts WHERE username = :u AND is_active = True"
            ),
            {"u": legacy_username_hash},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    try:
        legacy_password_key = legacy_generate_secret(entropy, password)
        seed = legacy_decrypt_secret(legacy_password_key, row["user_otp_hash"])
    except Exception as exc:  # noqa: BLE001 - legacy AES padding/format errors
        raise LegacyDecryptionError(str(exc)) from exc

    active_until = row["active_until"]
    if isinstance(active_until, str):
        # Postgres drivers (psycopg2/asyncpg) hand back a real datetime for a
        # timestamptz column; some other DBAPIs (e.g. sqlite3, used in tests)
        # return the raw string instead. Normalize either way.
        active_until = dt.datetime.fromisoformat(active_until)
    return seed, active_until
