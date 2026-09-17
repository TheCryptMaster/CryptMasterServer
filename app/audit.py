"""Writes to event_log. v1 defined the table but nothing ever inserted into
it; the "display logs" requirement needs it actually populated."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EventLog


async def log_event(
    session: AsyncSession, event_type: str, details: str, significant: bool = False
) -> None:
    session.add(EventLog(event_type=event_type, details=details, significant=significant))
    await session.flush()
