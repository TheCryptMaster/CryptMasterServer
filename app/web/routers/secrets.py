"""Manage stored secrets. Values are write-only from the web UI's
perspective: the API never returns a secret's value once stored, only its
name, active state, and which servers have ACL access to it."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import log_event
from app.config import settings
from app.crypto import blind_index, decrypt_field, encrypt_field
from app.db import get_session
from app.models import AppServer, Secret, SecretAcl
from app.web.deps import ALL_ROLES, require_role
from app.web.schemas import CreateSecretRequest, GrantAccessRequest, SecretOut

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


@router.get("", response_model=list[SecretOut])
async def list_secrets(current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)):
    secrets = (await session.execute(select(Secret))).scalars().all()
    out = []
    for secret in secrets:
        acl_rows = (
            await session.execute(
                select(SecretAcl.server_id).where(SecretAcl.secret_id == secret.id, SecretAcl.is_active.is_(True))
            )
        ).scalars()
        out.append(
            SecretOut(
                id=secret.id,
                name=decrypt_field(settings.master_key, "secret_name", secret.secret_name_enc),
                is_active=secret.is_active,
                server_ids_with_access=list(acl_rows),
            )
        )
    return out


@router.post("", response_model=SecretOut)
async def create_secret(
    payload: CreateSecretRequest,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    index = blind_index(settings.master_key, "secret_name", payload.name)
    existing = await session.execute(select(Secret.id).where(Secret.secret_name_index == index))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A secret with this name already exists")

    secret = Secret(
        secret_name_enc=encrypt_field(settings.master_key, "secret_name", payload.name),
        secret_name_index=index,
        secret_value_enc=encrypt_field(settings.master_key, "secret_value", payload.value),
    )
    session.add(secret)
    await session.flush()
    await log_event(session, "secret_created", f"name={payload.name} by user_id={current.user_id}")
    return SecretOut(id=secret.id, name=payload.name, is_active=True, server_ids_with_access=[])


@router.delete("/{secret_id}")
async def delete_secret(
    secret_id: int, current=Depends(require_role(*ALL_ROLES)), session: AsyncSession = Depends(get_session)
):
    secret = await session.get(Secret, secret_id)
    if secret is None:
        raise HTTPException(status_code=404, detail="No such secret")
    secret.is_active = False
    await log_event(session, "secret_deleted", f"secret_id={secret_id} by user_id={current.user_id}")
    return {"ok": True}


@router.post("/grant")
async def grant_access(
    payload: GrantAccessRequest,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    server = await session.get(AppServer, payload.server_id)
    secret = await session.get(Secret, payload.secret_id)
    if server is None or secret is None:
        raise HTTPException(status_code=404, detail="No such server or secret")
    existing = await session.execute(
        select(SecretAcl).where(SecretAcl.server_id == payload.server_id, SecretAcl.secret_id == payload.secret_id)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        row.is_active = True
    else:
        session.add(SecretAcl(server_id=payload.server_id, secret_id=payload.secret_id, is_active=True))
    await log_event(
        session, "secret_access_granted", f"server_id={payload.server_id} secret_id={payload.secret_id} by user_id={current.user_id}"
    )
    return {"ok": True}


@router.post("/revoke")
async def revoke_access(
    payload: GrantAccessRequest,
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(SecretAcl).where(SecretAcl.server_id == payload.server_id, SecretAcl.secret_id == payload.secret_id)
    )
    row = existing.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No such grant")
    row.is_active = False
    await log_event(
        session, "secret_access_revoked", f"server_id={payload.server_id} secret_id={payload.secret_id} by user_id={current.user_id}"
    )
    return {"ok": True}
