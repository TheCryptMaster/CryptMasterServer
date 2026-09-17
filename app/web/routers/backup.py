"""Database export for the portable encrypted backup feature.

This endpoint returns the *plaintext* (decrypted) database contents in the
HTTPS response body -- see app/backup.py's module docstring for why that's
the correct design, not an oversight. The browser is responsible for turning
this into an encrypted file (BIP-39 seed + PBKDF2 + AES-256-GCM, entirely
client-side); the server never sees the seed or passphrase and never writes
this payload to disk.

Because this hands back everything in the vault in one shot, it requires
step-up auth (password + a fresh OTP code) on top of an already-valid admin
session, and is restricted to the "admin" role -- an operator can manage
day-to-day servers/secrets but cannot walk off with a full export.
"""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.backup import export_database
from app.config import settings
from app.crypto import DecryptionError
from app.db import get_session
from app.models import User
from app.password_crypto import decrypt_with_password
from app.web.deps import ROLE_ADMIN, require_role
from app.web.schemas import BackupExportRequest, BackupExportResponse

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("/export", response_model=BackupExportResponse)
async def export_backup(
    payload: BackupExportRequest,
    current=Depends(require_role(ROLE_ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, current.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        seed = decrypt_with_password(payload.password, user.otp_seed_enc)
    except DecryptionError:
        raise HTTPException(status_code=401, detail="Password is incorrect")
    if not pyotp.TOTP(seed).verify(otp=payload.otp, valid_window=settings.totp_window):
        raise HTTPException(status_code=401, detail="OTP is incorrect")

    data = await export_database(session)
    await log_event(session, "backup_exported", f"user_id={user.id}", significant=True)
    return BackupExportResponse(data=data)
