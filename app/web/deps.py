"""FastAPI dependencies for the admin web API: session lookup + RBAC."""
from __future__ import annotations

from fastapi import Cookie, HTTPException

from app.web.session import SessionData, get_session

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ALL_ROLES = (ROLE_ADMIN, ROLE_OPERATOR)


async def current_session(cm_session: str | None = Cookie(default=None)) -> SessionData:
    session = await get_session(cm_session)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


async def current_session_allow_password_change(
    cm_session: str | None = Cookie(default=None),
) -> SessionData:
    """Like current_session, but doesn't block on must_change_password --
    used only by the change-password endpoint itself."""
    session = await get_session(cm_session)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


def require_role(*roles: str):
    async def _dependency(cm_session: str | None = Cookie(default=None)) -> SessionData:
        session = await get_session(cm_session)
        if session is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if session.must_change_password:
            raise HTTPException(status_code=403, detail="Password change required")
        if session.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return session

    return _dependency
