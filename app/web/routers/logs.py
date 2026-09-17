from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import EventLog
from app.web.deps import ALL_ROLES, require_role
from app.web.schemas import LogEntryOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[LogEntryOut])
async def list_logs(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current=Depends(require_role(*ALL_ROLES)),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(EventLog).order_by(EventLog.event_timestamp.desc()).limit(limit).offset(offset)
        )
    ).scalars()
    return [
        LogEntryOut(
            id=row.id,
            event_type=row.event_type,
            significant=row.significant,
            details=row.details,
            timestamp=row.event_timestamp.isoformat(),
        )
        for row in rows
    ]
