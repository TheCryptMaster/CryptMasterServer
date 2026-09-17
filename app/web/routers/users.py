"""Manage admin-console user accounts. Creating a user or changing anyone's
role is admin-only; an operator can see the list but not touch it."""
from __future__ import annotations

import datetime as dt

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.config import settings
from app.crypto import blind_index, decrypt_field, encrypt_field
from app.db import get_session
from app.models import User
from app.password_crypto import encrypt_with_password
from app.web.deps import ALL_ROLES, ROLE_ADMIN, require_role
from app.web.schemas import CreateUserRequest, CreateUserResponse, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=decrypt_field(settings.master_key, "username", user.username_enc),
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        active_until=user.active_until.isoformat(),
    )


@router.get("", response_model=list[UserOut])
async def list_users(current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)):
    users = (await session.execute(select(User))).scalars().all()
    return [_user_out(u) for u in users]


@router.post("", response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    current=Depends(require_role(ROLE_ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    if payload.role not in ("admin", "operator"):
        raise HTTPException(status_code=400, detail="role must be admin or operator")

    email = payload.email.strip().lower()
    index = blind_index(settings.master_key, "username", email)
    existing = await session.execute(select(User.id).where(User.username_index == index))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    import secrets as pysecrets

    temporary_password = pysecrets.token_urlsafe(18)
    seed = pyotp.random_base32()
    session.add(
        User(
            username_enc=encrypt_field(settings.master_key, "username", email),
            username_index=index,
            otp_seed_enc=encrypt_with_password(temporary_password, seed),
            role=payload.role,
            must_change_password=True,
            active_until=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=payload.active_days),
        )
    )
    await log_event(session, "user_created", f"email={email} role={payload.role} by user_id={current.user_id}")
    provisioning_uri = pyotp.TOTP(seed).provisioning_uri(name=email, issuer_name=settings.totp_issuer)
    return CreateUserResponse(provisioning_uri=provisioning_uri, temporary_password=temporary_password)


@router.post("/{user_id}/disable")
async def disable_user(
    user_id: int, current=Depends(require_role(ROLE_ADMIN)), session: AsyncSession = Depends(get_session)
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="No such user")
    if user.id == current.user_id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = False
    await log_event(session, "user_disabled", f"user_id={user_id} by user_id={current.user_id}")
    return {"ok": True}


@router.post("/{user_id}/role")
async def set_user_role(
    user_id: int,
    role: str,
    current=Depends(require_role(ROLE_ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    if role not in ("admin", "operator"):
        raise HTTPException(status_code=400, detail="role must be admin or operator")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="No such user")
    user.role = role
    await log_event(session, "user_role_changed", f"user_id={user_id} role={role} by user_id={current.user_id}")
    return {"ok": True}
