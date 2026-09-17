#!/usr/bin/env python3
"""Crypt Master Server v2 -- FastAPI application.

Key differences from v1 (see repo README / MIGRATION.md for the full list):
  * No f-string SQL; every query is parameterized via SQLAlchemy.
  * No process-global lockout state; lockouts are per-identity, in Redis,
    and survive restarts / multiple workers.
  * Encryption uses HKDF + AES-256-GCM with a per-value random salt, not a
    seeded `random.Random` instance reused across every row.
  * `secret_acl` is actually enforced.
  * CORS is not wildcarded.
  * Async all the way through (routes, DB session, Redis).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AuthError,
    authenticate_user,
    get_secret_for_server,
    initiate_server_auth,
    validate_server_secret,
)
from app.config import settings
from app.crypto import blind_index, encrypt_field
from app.db import get_session
from app.models import PendingEnrollment
from app.schemas import (
    EnableApiRequest,
    EnableApiResponse,
    EnrollServerRequest,
    GetSecretRequest,
    GetSecretResponse,
    StartAuthRequest,
    StartAuthResponse,
)
from app.security import (
    clear_failures,
    is_locked,
    is_system_open,
    mark_system_open,
    record_failure,
)
from sqlalchemy import select, update
import json

logger = logging.getLogger("cryptmaster")


@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter_client)
    yield
    await FastAPILimiter.close()


app = FastAPI(title="Crypt Master Server", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/v2/start_auth", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def start_auth(
    request: Request,
    payload: StartAuthRequest,
    session: AsyncSession = Depends(get_session),
):
    ip = client_ip(request)
    allowed, nonce = await initiate_server_auth(session, payload.system_id, ip)
    if not allowed:
        logger.warning("start_auth rejected for system_id=%s ip=%s", payload.system_id, ip)
        raise HTTPException(status_code=401, detail="Unauthorized")
    return StartAuthResponse(response="Awaiting Key", nonce=nonce)


@app.post("/v2/enable_api", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
async def enable_api(
    request: Request,
    payload: EnableApiRequest,
    session: AsyncSession = Depends(get_session),
):
    ip = client_ip(request)
    identity = blind_index(settings.master_key, "username", payload.user_name.lower())

    if await is_locked("login", identity) or await is_locked("login", ip):
        raise HTTPException(status_code=403, detail="Account temporarily locked")

    try:
        active_until = await authenticate_user(
            session, payload.user_name.lower(), payload.user_pass, payload.otp
        )
    except AuthError as exc:
        logger.warning("login failed user=%s ip=%s reason=%s", payload.user_name, ip, exc.message)
        await record_failure("login", identity)
        await record_failure("login", ip)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    await clear_failures("login", identity)
    await clear_failures("login", ip)
    expiry_str = await mark_system_open()
    logger.info("login success user=%s ip=%s", payload.user_name, ip)
    return EnableApiResponse(response="Success", active_until=expiry_str)


@app.post("/v2/enroll_server", dependencies=[Depends(RateLimiter(times=1, seconds=120))])
async def enroll_server(
    request: Request,
    payload: EnrollServerRequest,
    session: AsyncSession = Depends(get_session),
):
    ip = client_ip(request)
    system_id_index = blind_index(settings.master_key, "system_id", payload.system_id)

    result = await session.execute(
        select(PendingEnrollment).where(PendingEnrollment.system_id_index == system_id_index)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        new_attempts = existing.enrollment_attempts + 1
        await session.execute(
            update(PendingEnrollment)
            .where(PendingEnrollment.id == existing.id)
            .values(enrollment_attempts=new_attempts)
        )
        if new_attempts > 3:
            return {"response": "This server has been banned"}
        return {"response": "enrollment is still pending"}

    payload_blob = encrypt_field(
        settings.master_key,
        "enrollment",
        json.dumps({"system_id": payload.system_id, "system_salt": payload.system_salt, "ip_address": ip}),
    )
    session.add(
        PendingEnrollment(system_id_index=system_id_index, payload_enc=payload_blob)
    )
    return {"response": "enrollment pending"}


@app.post("/v2/get_secret", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def get_secret(
    request: Request,
    payload: GetSecretRequest,
    session: AsyncSession = Depends(get_session),
):
    ip = client_ip(request)
    identity = blind_index(settings.master_key, "system_id", payload.system_id)

    if await is_locked("secret", identity) or await is_locked("secret", ip):
        raise HTTPException(status_code=403, detail="API disabled")

    if not await validate_server_secret(payload.system_id, payload.auth_response):
        # Note: system_id here is used only as a display/log field; the real
        # nonce is opaque and consumed inside validate_server_secret via the
        # value the client echoes back as part of auth_response's challenge.
        logger.warning("get_secret auth failed system_id=%s ip=%s", payload.system_id, ip)
        await record_failure("secret", identity)
        await record_failure("secret", ip)
        raise HTTPException(status_code=403, detail="ACCESS DENIED")

    if not await is_system_open():
        return GetSecretResponse(response="Authorized user must provide OTP")

    secret = await get_secret_for_server(session, payload.system_id, ip, payload.requested_password)
    if secret is None:
        return GetSecretResponse(response="No secret found")

    await clear_failures("secret", identity)
    await clear_failures("secret", ip)
    return GetSecretResponse(response="SUCCESS", secret=secret)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        ssl_keyfile=settings.tls_keyfile,
        ssl_certfile=settings.tls_certfile,
        reload=False,
    )
