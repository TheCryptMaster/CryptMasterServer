"""First-run setup: is this a fresh install, and if so, create a new empty
vault or restore one from a portable backup.

Both create/restore are only permitted while `initialized` is false (i.e. no
user row exists yet), so this can't be used to nuke a running vault.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.backup import import_database
from app.config import settings
from app.crypto import encrypt_field
from app.db import get_session
from app.models import SystemConfig, User
from app.web.bootstrap import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, create_default_admin
from app.web.schemas import (
    BackupRestoreRequest,
    CreateDatabaseRequest,
    DefaultAdminInfo,
    SetupStatus,
)

router = APIRouter(prefix="/api/setup", tags=["setup"])


async def _is_initialized(session: AsyncSession) -> bool:
    count = await session.scalar(select(func.count()).select_from(User))
    return bool(count)


@router.get("/status", response_model=SetupStatus)
async def status(session: AsyncSession = Depends(get_session)):
    return SetupStatus(initialized=await _is_initialized(session))


@router.post("/create-database", response_model=DefaultAdminInfo)
async def create_database(payload: CreateDatabaseRequest, session: AsyncSession = Depends(get_session)):
    if await _is_initialized(session):
        raise HTTPException(status_code=409, detail="Already initialized")

    session.add(
        SystemConfig(
            host_name_enc=encrypt_field(settings.master_key, "hostname", payload.host_name),
            domain_name_enc=encrypt_field(settings.master_key, "domain", payload.domain_name),
            schema_version="2.0.0",
        )
    )
    await create_default_admin(session)
    await log_event(session, "database_created", "fresh install")

    return DefaultAdminInfo(
        username=DEFAULT_ADMIN_USERNAME,
        password=DEFAULT_ADMIN_PASSWORD,
        note="Log in with these now. You will be required to set a new password and enroll a real authenticator app immediately.",
    )


@router.post("/restore-database")
async def restore_database(payload: BackupRestoreRequest, session: AsyncSession = Depends(get_session)):
    if await _is_initialized(session):
        raise HTTPException(status_code=409, detail="Already initialized")

    try:
        await import_database(session, payload.data)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid backup data: {exc}") from exc

    if not await _is_initialized(session):
        raise HTTPException(status_code=400, detail="Backup contained no users; refusing to leave the vault with no admin")

    await log_event(session, "database_restored", f"restored_at={dt.datetime.now(dt.timezone.utc).isoformat()}")
    return {"ok": True}
