"""Manage enrolled app servers and their IP allow-lists."""
from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.config import settings
from app.crypto import blind_index, decrypt_field, encrypt_field
from app.db import get_session
from app.models import AppServer, AppServerIp, PendingEnrollment
from app.web.deps import ALL_ROLES, require_role
from app.web.schemas import (
    AddServerIpRequest,
    CreateServerRequest,
    PendingEnrollmentOut,
    ServerOut,
)

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _server_out(server: AppServer, ips: list[str]) -> ServerOut:
    return ServerOut(
        id=server.id,
        system_id=decrypt_field(settings.master_key, "system_id", server.server_name_enc),
        label=server.label,
        is_active=server.is_active,
        active_until=server.active_until.isoformat(),
        ip_addresses=ips,
    )


@router.get("", response_model=list[ServerOut])
async def list_servers(current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)):
    servers = (await session.execute(select(AppServer))).scalars().all()
    out = []
    for server in servers:
        ip_rows = (
            await session.execute(select(AppServerIp).where(AppServerIp.server_id == server.id, AppServerIp.is_active.is_(True)))
        ).scalars()
        ips = [decrypt_field(settings.master_key, "ip_address", ip.ip_address_enc) for ip in ip_rows]
        out.append(_server_out(server, ips))
    return out


@router.post("", response_model=ServerOut)
async def create_server(
    payload: CreateServerRequest,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    index = blind_index(settings.master_key, "system_id", payload.system_id)
    existing = await session.execute(select(AppServer.id).where(AppServer.server_name_index == index))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A server with this system_id is already enrolled")

    server = AppServer(
        server_name_enc=encrypt_field(settings.master_key, "system_id", payload.system_id),
        server_name_index=index,
        server_salt_enc=encrypt_field(settings.master_key, "server_salt", payload.server_salt),
        label=payload.label,
        active_until=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=60),
    )
    session.add(server)
    await session.flush()
    for ip in payload.ip_addresses:
        session.add(
            AppServerIp(
                server_id=server.id,
                ip_address_enc=encrypt_field(settings.master_key, "ip_address", ip),
                ip_address_index=blind_index(settings.master_key, "ip_address", ip),
            )
        )
    await log_event(session, "server_created", f"system_id={payload.system_id} by user_id={current.user_id}")
    return _server_out(server, payload.ip_addresses)


@router.post("/{server_id}/ips", response_model=ServerOut)
async def add_server_ip(
    server_id: int,
    payload: AddServerIpRequest,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    server = await session.get(AppServer, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="No such server")
    session.add(
        AppServerIp(
            server_id=server.id,
            ip_address_enc=encrypt_field(settings.master_key, "ip_address", payload.ip_address),
            ip_address_index=blind_index(settings.master_key, "ip_address", payload.ip_address),
        )
    )
    await session.flush()
    await log_event(session, "server_ip_added", f"server_id={server_id} by user_id={current.user_id}")
    ip_rows = (
        await session.execute(select(AppServerIp).where(AppServerIp.server_id == server.id, AppServerIp.is_active.is_(True)))
    ).scalars()
    ips = [decrypt_field(settings.master_key, "ip_address", ip.ip_address_enc) for ip in ip_rows]
    return _server_out(server, ips)


@router.delete("/{server_id}/ips/{ip_id}")
async def remove_server_ip(
    server_id: int,
    ip_id: int,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    ip_row = await session.get(AppServerIp, ip_id)
    if ip_row is None or ip_row.server_id != server_id:
        raise HTTPException(status_code=404, detail="No such IP entry")
    ip_row.is_active = False
    await log_event(session, "server_ip_removed", f"server_id={server_id} ip_id={ip_id} by user_id={current.user_id}")
    return {"ok": True}


@router.delete("/{server_id}")
async def delete_server(
    server_id: int, current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)
):
    server = await session.get(AppServer, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="No such server")
    server.is_active = False
    await log_event(session, "server_disabled", f"server_id={server_id} by user_id={current.user_id}")
    return {"ok": True}


@router.get("/pending", response_model=list[PendingEnrollmentOut])
async def list_pending(current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(PendingEnrollment).where(
                PendingEnrollment.enrollment_complete.is_(False), PendingEnrollment.is_expired.is_(False)
            )
        )
    ).scalars()
    out = []
    for row in rows:
        payload = json.loads(decrypt_field(settings.master_key, "enrollment", row.payload_enc))
        out.append(
            PendingEnrollmentOut(
                id=row.id,
                system_id=payload["system_id"],
                ip_address=payload["ip_address"],
                requested_at=row.date_requested.isoformat(),
                attempts=row.enrollment_attempts,
            )
        )
    return out


@router.post("/pending/{enrollment_id}/approve", response_model=ServerOut)
async def approve_pending(
    enrollment_id: int,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(PendingEnrollment, enrollment_id)
    if row is None or row.enrollment_complete:
        raise HTTPException(status_code=404, detail="No such pending enrollment")
    payload = json.loads(decrypt_field(settings.master_key, "enrollment", row.payload_enc))
    row.enrollment_complete = True

    server = AppServer(
        server_name_enc=encrypt_field(settings.master_key, "system_id", payload["system_id"]),
        server_name_index=blind_index(settings.master_key, "system_id", payload["system_id"]),
        server_salt_enc=encrypt_field(settings.master_key, "server_salt", payload["system_salt"]),
        active_until=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=60),
    )
    session.add(server)
    await session.flush()
    session.add(
        AppServerIp(
            server_id=server.id,
            ip_address_enc=encrypt_field(settings.master_key, "ip_address", payload["ip_address"]),
            ip_address_index=blind_index(settings.master_key, "ip_address", payload["ip_address"]),
        )
    )
    await log_event(session, "server_enrollment_approved", f"system_id={payload['system_id']} by user_id={current.user_id}")
    return _server_out(server, [payload["ip_address"]])


@router.post("/pending/{enrollment_id}/reject")
async def reject_pending(
    enrollment_id: int, current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)
):
    row = await session.get(PendingEnrollment, enrollment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No such pending enrollment")
    row.is_expired = True
    await log_event(session, "server_enrollment_rejected", f"enrollment_id={enrollment_id} by user_id={current.user_id}")
    return {"ok": True}
