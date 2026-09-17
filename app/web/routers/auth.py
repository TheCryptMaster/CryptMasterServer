"""Web session login, forced first-login password change, and OTP
enrollment/re-enrollment.

Every password change (forced or voluntary) rotates the user's OTP seed too,
since the seed is encrypted with a key derived from the password -- changing
one always means re-deriving the other. The new seed is staged in Redis
(short TTL) until the admin proves they captured it by entering one valid
code via /confirm-otp; only then does the DB row's must_change_password flag
clear and the seed become "live" for real logins. This mirrors the same
write-down-then-prove-it pattern used for the backup seed.
"""
from __future__ import annotations

import datetime as dt

import pyotp
import redis.asyncio as redis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.config import settings
from app.crypto import DecryptionError, blind_index, decrypt_field
from app.db import get_session
from app.models import User
from app.password_crypto import decrypt_with_password, encrypt_with_password
from app.security import clear_failures, is_locked, record_failure
from app.web.deps import current_session, current_session_allow_password_change
from app.web.schemas import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmOtpRequest,
    LoginRequest,
    LoginResponse,
    WhoAmIResponse,
)
from app.web.session import SESSION_COOKIE_NAME, SessionData, create_session, destroy_session, refresh_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

_redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


def _pending_otp_key(session_token: str) -> str:
    return f"cryptmaster:pending_otp:{session_token}"


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)
):
    username_index = blind_index(settings.master_key, "username", payload.username.lower())

    if await is_locked("web_login", username_index):
        raise HTTPException(status_code=403, detail="Account temporarily locked")

    result = await session.execute(
        select(User).where(User.username_index == username_index, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        await record_failure("web_login", username_index)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        seed = decrypt_with_password(payload.password, user.otp_seed_enc)
    except DecryptionError:
        await record_failure("web_login", username_index)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.must_change_password:
        # Normal path: a real OTP must already be enrolled and verified.
        if not payload.otp or not pyotp.TOTP(seed).verify(otp=payload.otp, valid_window=settings.totp_window):
            await record_failure("web_login", username_index)
            raise HTTPException(status_code=401, detail="Invalid credentials")

    await clear_failures("web_login", username_index)
    token = await create_session(user.id, user.role, user.must_change_password)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=8 * 60 * 60,
    )
    await log_event(session, "web_login", f"user_id={user.id} must_change_password={user.must_change_password}")
    return LoginResponse(must_change_password=user.must_change_password, role=user.role)


@router.post("/logout")
async def logout(response: Response, cm_session: str | None = Cookie(default=None)):
    if cm_session:
        await destroy_session(cm_session)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(current=Depends(current_session)):
    return WhoAmIResponse(role=current.role, must_change_password=current.must_change_password)


async def _stage_new_otp(session_token: str, seed: str) -> None:
    await _redis.set(_pending_otp_key(session_token), seed, ex=300)


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    cm_session: str | None = Cookie(default=None),
    current=Depends(current_session_allow_password_change),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, current.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        old_seed = decrypt_with_password(payload.current_password, user.otp_seed_enc)
    except DecryptionError:
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if not current.must_change_password:
        # Voluntary change (not the forced first-login flow): the existing
        # OTP must also be proven before we let the password rotate.
        if not payload.current_otp or not pyotp.TOTP(old_seed).verify(
            otp=payload.current_otp, valid_window=settings.totp_window
        ):
            raise HTTPException(status_code=401, detail="Current OTP is incorrect")

    new_seed = pyotp.random_base32()
    user.otp_seed_enc = encrypt_with_password(payload.new_password, new_seed)
    user.must_change_password = True  # stays true until /confirm-otp succeeds
    await session.flush()

    await _stage_new_otp(cm_session, new_seed)
    await refresh_session(cm_session, SessionData(current.user_id, current.role, True))
    await log_event(session, "password_changed", f"user_id={user.id}")

    username = decrypt_field(settings.master_key, "username", user.username_enc)
    provisioning_uri = pyotp.TOTP(new_seed).provisioning_uri(name=username, issuer_name=settings.totp_issuer)
    return ChangePasswordResponse(provisioning_uri=provisioning_uri)


@router.post("/confirm-otp")
async def confirm_otp(
    payload: ConfirmOtpRequest,
    cm_session: str | None = Cookie(default=None),
    current=Depends(current_session_allow_password_change),
    session: AsyncSession = Depends(get_session),
):
    if not cm_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    seed = await _redis.get(_pending_otp_key(cm_session))
    if seed is None:
        raise HTTPException(status_code=400, detail="No pending OTP enrollment; change your password again")

    if not pyotp.TOTP(seed).verify(otp=payload.otp, valid_window=settings.totp_window):
        raise HTTPException(status_code=400, detail="Invalid code")

    user = await session.get(User, current.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.must_change_password = False
    await session.flush()

    await _redis.delete(_pending_otp_key(cm_session))
    await refresh_session(cm_session, SessionData(current.user_id, current.role, False))
    await log_event(session, "otp_enrollment_confirmed", f"user_id={user.id}")
    return {"ok": True}
