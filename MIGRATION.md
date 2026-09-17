# Migrating from v1 to v2

## What changed, and why

| v1 | v2 | Why |
|---|---|---|
| f-string SQL everywhere | SQLAlchemy bound parameters | v1 was SQL-injectable through nearly every endpoint |
| `generate_secret()`: seeded `random.Random`, same key reused across every row of a field type | HKDF-SHA256 + AES-256-GCM, unique random salt per value | `random` isn't cryptographically secure, and key reuse across rows is a real weakness |
| DB password derived from a hashed `/dev/disk/by-uuid` listing | Plain generated password in `.env` / compose secret | Hardware-serial parsing was fragile and broke silently on disk changes |
| `fail_count`/`fail_disable`/`active_until` as module globals | Per-identity counters in Redis with TTL | Globals meant one bad login locked out every user, and reset on restart |
| `secret_acl` table defined but never checked | Enforced on every `get_secret` call | Any enrolled server could previously fetch any secret |
| `CORS allow_origins=['*']` with credentials | Explicit origin allow-list, no credentials | Wildcard + credentials defeats the point of CORS |
| Client `verify=False` hardcoded | TLS verification on by default | v1's "secure" client silently accepted any certificate |
| `add_remove.py` (v1 CLI, wrote to a plaintext `.authenticated_users` file, bypassing the DB) | `cli/manage.py`, one tool, always through the DB | Two divergent, undocumented ways to create users |

## Why migration needs a manifest, not just a DB connection

v1 stored secret names, server system_ids, and IP addresses as
`generate_secret(value)` -- a one-way, PRNG-derived hash used purely as a
lookup key. It is **not reversible**: you cannot go from the stored hash
back to the original secret name or system_id. The *values* behind them
(the actual secret, the server's enrollment salt) are genuinely encrypted
and recoverable, but only once you already know the name/id to re-derive
the same lookup hash.

This was never a practical limitation in v1 -- every caller already had to
know the secret name or its own system_id to ask for it. `migration/migrate_v1_to_v2.py`
asks the same of you, via a manifest file.

User TOTP seeds are a harder case: they were encrypted with a key derived
from the user's login password, which the server never stored. There is no
way to recover a seed without that password. You can supply it transiently
in the manifest for a scripted cutover, but re-enrolling each user via
`python -m cli.manage` (one QR scan) is simpler and starts them on the
stronger key derivation by default.

## Two ways to run the migration

### Option A: the admin web console's first-run flow

A brand-new, uninitialized v2 server offers three setup options: create an
empty vault, restore a portable backup, or **migrate from a legacy server**.
The third option is `POST /api/setup/migrate-legacy` -- it takes the same
inputs as the manifest below (old DB connection string, old `.entropy`
contents, and the secrets/servers/users lists) directly in the request body,
runs the migration inline, and reports counts back to the browser. It's
disabled the moment the vault is initialized, so it can't be used against a
running system. If the manifest's `users` list is empty (or every entry
fails), the endpoint falls back to creating the same default admin
credentials the "create empty vault" option would, so you're never left with
data but no way to log in.

Migrated users keep their **original password and authenticator app codes**
-- no forced rotation, unlike the default-credentials path -- since their
OTP seed is decrypted with their existing password and re-encrypted with
that same password, unchanged. They're also all granted the `admin` role,
since v1 had no role concept: everyone who could open the vault had full
authority over it.

### Option B: the CLI tool, for a scripted/offline cutover

1. Stand up the new database and apply migrations (`alembic upgrade head`).
2. Keep the v1 `.entropy` file and v1 database reachable (read-only) during
   the cutover window.
3. Write `manifest.json`:

   ```json
   {
     "secrets": ["stripe_api_key", "db_backup_password"],
     "app_servers": [{"system_id": "<value the client computed>", "ip_address": "10.0.0.5"}],
     "users": [{"email": "admin@example.com", "password": "<their current password>"}]
   }
   ```

4. Dry run first:

   ```bash
   python -m migration.migrate_v1_to_v2 \
     --old-dsn postgresql://cryptmaster:oldpass@old-host:5432/cryptmaster_db \
     --old-entropy-file /path/to/.entropy \
     --manifest manifest.json \
     --dry-run
   ```

5. Review the output, then re-run without `--dry-run` to actually write into
   the new database. The tool skips anything already present, so it's safe
   to re-run.
6. Re-enroll any user not listed in the manifest, and re-point app servers'
   `CryptMaster` client config at the new host once you're satisfied.
7. Decommission the v1 server and shred the old `.entropy` file.

Both options share the same read path (`migration/legacy_reader.py`) and
write path (`migration/writer.py`); the CLI and the web endpoint are just
different front ends over the same logic.
