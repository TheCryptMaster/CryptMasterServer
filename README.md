# Crypt Master Server v2

A self-hosted secrets vault: app servers fetch credentials from a hardened
gatekeeper instead of keeping them in local config. The Crypt Master client
library is at https://github.com/TheCryptMaster/CryptMaster.

**This is a ground-up rewrite of the original (v1) implementation.** The old
code is preserved, unmodified, on the [`legacy-v1`](../../tree/legacy-v1)
branch, for reference and for the migration tool below. See
[`MIGRATION.md`](./MIGRATION.md) for what changed and why, and for how to
move an existing v1 database over.

## Architecture

- FastAPI (async), SQLAlchemy 2.0 (async, parameterized queries only),
  Alembic migrations, Postgres, Redis.
- Field-level encryption: HKDF-SHA256 + AES-256-GCM, unique salt per value,
  derived from a single master key that lives only in `.env` (see
  `.env.example`). Lookup columns (username, server id, ip, secret name) use
  a separate keyed blind index so we can query by exact match without ever
  decrypting a whole table or string-formatting a value into SQL.
- Rate limiting and lockouts are per-identity, stored in Redis with a TTL --
  not process-global variables, so they survive restarts and work correctly
  with more than one worker.
- `secret_acl` is enforced: an enrolled app server can only fetch secrets
  it's been explicitly granted.

## Local setup

```bash
cp .env.example .env
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
# paste the output into .env as MASTER_KEY_B64

export POSTGRES_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(24))")
docker compose up -d db redis
alembic upgrade head

python -m cli.manage   # add your first admin user, add a secret, enroll a server
docker compose up -d api
```

The physical/network hardening guidance from v1's README (dedicated
hardware, isolated subnet, firewall rules, disk encryption) still applies --
none of that changed, only the application code did.

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Admin CLI

`python -m cli.manage` replaces v1's `add_remove.py` and `setup.py` with a
single tool that talks to the real database through the ORM (no more
plaintext `.authenticated_users` file, no more f-string SQL).

## Admin web console

v1 had no web UI at all. `web/` is a React admin console covering
first-run setup (create a vault, restore a backup, or migrate from a
legacy v1 server), server enrollment with IP allow-lists, users, secrets,
activity logs, and the portable encrypted backup feature. See
[`web/README.md`](./web/README.md) for how to run it; it talks to the
`/api/*` routes added alongside the existing `/v2/*` server-to-server API.
