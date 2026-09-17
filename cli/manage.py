#!/usr/bin/env python3
"""Admin CLI: manage users, servers, and secrets.

Replaces v1's *three* divergent tools:
  * add_remove.py (v1, wrote OTP seeds to a plaintext `.authenticated_users`
    file, bypassing the database entirely)
  * setup.py (v1, half-finished, wrote to the DB but with f-string SQL)
  * seed_manager.py / add_remove.py's QR flow

Everything here goes through the same async ORM models and encryption used
by the running server, with real bind parameters and pydantic-validated
input. Run with: python -m cli.manage
"""
from __future__ import annotations

import asyncio
import io
import sys
from datetime import datetime, timedelta, timezone
from getpass import getpass

import pyotp
import qrcode
from password_strength import PasswordPolicy
from sqlalchemy import select

from app.config import settings
from app.crypto import blind_index, encrypt_field
from app.db import session_scope
from app.models import AppServer, PendingEnrollment, Secret, SecretAcl, User
from app.password_crypto import encrypt_with_password

PASS_POLICY = PasswordPolicy.from_names(length=12, uppercase=1, numbers=1, special=1, nonletters=1)


def display_qr(provisioning_uri: str) -> None:
    qr = qrcode.QRCode()
    qr.add_data(provisioning_uri)
    buf = io.StringIO()
    qr.print_ascii(out=buf)
    buf.seek(0)
    print(buf.read())


async def add_user() -> None:
    email = input("User email: ").strip().lower()
    async with session_scope() as session:
        existing = await session.execute(
            select(User.id).where(User.username_index == blind_index(settings.master_key, "username", email))
        )
        if existing.scalar_one_or_none() is not None:
            print("User already exists.")
            return

    for _ in range(3):
        password = getpass("New user password: ")
        violations = PASS_POLICY.test(password)
        if violations:
            print(f"Password too weak: {violations}")
            continue
        if getpass("Confirm password: ") != password:
            print("Passwords do not match.")
            continue
        break
    else:
        print("Too many failed attempts.")
        return

    expiry_days_raw = input("Account active for how many days? (default 365): ").strip()
    expiry_days = int(expiry_days_raw) if expiry_days_raw else 365

    seed = pyotp.random_base32()
    provisioning_uri = pyotp.TOTP(seed).provisioning_uri(name=email, issuer_name=settings.totp_issuer)

    async with session_scope() as session:
        session.add(
            User(
                username_enc=encrypt_field(settings.master_key, "username", email),
                username_index=blind_index(settings.master_key, "username", email),
                otp_seed_enc=encrypt_with_password(password, seed),
                active_until=datetime.now(timezone.utc) + timedelta(days=expiry_days),
            )
        )
    print("\nUser added. Scan this QR code with an authenticator app:\n")
    display_qr(provisioning_uri)


async def list_users() -> None:
    from app.crypto import decrypt_field

    async with session_scope() as session:
        result = await session.execute(select(User))
        for user in result.scalars():
            email = decrypt_field(settings.master_key, "username", user.username_enc)
            status = "active" if user.is_active and user.active_until > datetime.now(timezone.utc) else "expired/disabled"
            print(f"[{user.id}] {email} - {status} (until {user.active_until})")


async def remove_user() -> None:
    await list_users()
    user_id_raw = input("\nUser ID to remove (blank to cancel): ").strip()
    if not user_id_raw:
        return
    async with session_scope() as session:
        user = await session.get(User, int(user_id_raw))
        if user is None:
            print("No such user.")
            return
        user.is_active = False
    print("User disabled.")


async def approve_server(system_id: str, system_salt: str, ip_address: str, active_days: int = 60) -> None:
    async with session_scope() as session:
        session.add(
            AppServer(
                server_name_enc=encrypt_field(settings.master_key, "system_id", system_id),
                server_name_index=blind_index(settings.master_key, "system_id", system_id),
                ip_address_enc=encrypt_field(settings.master_key, "ip_address", ip_address),
                ip_address_index=blind_index(settings.master_key, "ip_address", ip_address),
                server_salt_enc=encrypt_field(settings.master_key, "server_salt", system_salt),
                active_until=datetime.now(timezone.utc) + timedelta(days=active_days),
            )
        )
    print("Server enrolled.")


async def list_pending_enrollments() -> None:
    import json

    from app.crypto import decrypt_field

    async with session_scope() as session:
        result = await session.execute(
            select(PendingEnrollment).where(
                PendingEnrollment.enrollment_complete.is_(False),
                PendingEnrollment.is_expired.is_(False),
            )
        )
        rows = list(result.scalars())
        if not rows:
            print("No pending enrollments.")
            return
        for row in rows:
            payload = json.loads(decrypt_field(settings.master_key, "enrollment", row.payload_enc))
            print(f"[{row.id}] {payload} requested {row.date_requested}")


async def approve_pending_enrollment() -> None:
    import json

    from app.crypto import decrypt_field

    await list_pending_enrollments()
    row_id_raw = input("\nEnrollment id to approve (blank to cancel): ").strip()
    if not row_id_raw:
        return
    async with session_scope() as session:
        row = await session.get(PendingEnrollment, int(row_id_raw))
        if row is None or row.enrollment_complete:
            print("No such pending enrollment.")
            return
        payload = json.loads(decrypt_field(settings.master_key, "enrollment", row.payload_enc))
        row.enrollment_complete = True
    await approve_server(payload["system_id"], payload["system_salt"], payload["ip_address"])


async def add_secret() -> None:
    name = input("Secret name: ").strip()
    value = getpass("Secret value: ")
    async with session_scope() as session:
        existing = await session.execute(
            select(Secret.id).where(Secret.secret_name_index == blind_index(settings.master_key, "secret_name", name))
        )
        if existing.scalar_one_or_none() is not None:
            print("Secret already exists.")
            return
        session.add(
            Secret(
                secret_name_index=blind_index(settings.master_key, "secret_name", name),
                secret_value_enc=encrypt_field(settings.master_key, "secret_value", value),
            )
        )
    print("Secret stored.")


async def grant_secret_access() -> None:
    server_index_raw = input("App server row id: ").strip()
    secret_index_raw = input("Secret row id: ").strip()
    async with session_scope() as session:
        session.add(
            SecretAcl(server_id=int(server_index_raw), secret_id=int(secret_index_raw), is_active=True)
        )
    print("Access granted.")


MENU = {
    "1": ("Add user", add_user),
    "2": ("List users", list_users),
    "3": ("Remove/disable user", remove_user),
    "4": ("List pending server enrollments", list_pending_enrollments),
    "5": ("Approve a pending server enrollment", approve_pending_enrollment),
    "6": ("Add secret", add_secret),
    "7": ("Grant server access to a secret", grant_secret_access),
}


async def main() -> None:
    while True:
        print("\nCrypt Master Admin\n" + "\n".join(f"{k}) {v[0]}" for k, v in MENU.items()) + "\nq) Quit")
        choice = input("> ").strip().lower()
        if choice == "q":
            return
        action = MENU.get(choice)
        if action is None:
            print("Invalid choice.")
            continue
        await action[1]()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
