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
    MigrateLegacyRequest,
    MigrateLegacyResponse,
    SetupStatus,
)
from migration.migrate_v1_to_v2 import run_migration

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


@router.post("/migrate-legacy", response_model=MigrateLegacyResponse)
async def migrate_legacy(payload: MigrateLegacyRequest, session: AsyncSession = Depends(get_session)):
    """Third first-run option: pull data straight from a reachable v1
    server's database instead of creating empty or restoring a backup file.

    Runs against the OLD database with a blocking (sync) SQLAlchemy engine,
    interleaved with async writes into the current database -- acceptable
    here because this only ever runs once, by a solo admin, during initial
    setup; it is never reachable once the vault is initialized.
    """
    if await _is_initialized(session):
        raise HTTPException(status_code=409, detail="Already initialized")

    counts = await run_migration(
        payload.old_dsn,
        payload.old_entropy,
        payload.secrets,
        [entry.model_dump() for entry in payload.app_servers],
        [entry.model_dump() for entry in payload.users],
        dry_run=payload.dry_run,
    )

    if not payload.dry_run and not await _is_initialized(session):
        # No users came over (empty/omitted manifest section, or all failed) --
        # fall back to default credentials rather than leave a populated but
        # unloggable-into vault.
        await create_default_admin(session)
        counts.errors.append(
            f"No users were migrated; created default admin credentials instead "
            f"({DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD} -- change immediately on first login)."
        )

    await log_event(
        session,
        "legacy_migration_run" if not payload.dry_run else "legacy_migration_dry_run",
        f"secrets={counts.secrets} app_servers={counts.app_servers} users={counts.users} failed={counts.failed}",
    )

    return MigrateLegacyResponse(
        secrets_migrated=counts.secrets,
        app_servers_migrated=counts.app_servers,
        users_migrated=counts.users,
        skipped=counts.skipped,
        failed=counts.failed,
        log=counts.errors,
    )
