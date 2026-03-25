"""
FastAPI 공통 의존성.
JWT 인증, 역할 검증.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.admin import AdminUser, AdminRole, SystemAdmin


async def get_current_admin(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """JWT Bearer 토큰에서 AdminUser 추출."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") == "system_admin":
        # SystemAdmin은 별도 처리 — 여기선 tenant-scoped API 접근 거부
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use system admin endpoints")

    user_id = payload.get("sub")
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id, AdminUser.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: AdminRole):
    """역할 검증 의존성 팩토리."""
    async def _check(user: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return _check


# 편의 의존성
require_editor = require_role(AdminRole.admin, AdminRole.editor)
require_admin = require_role(AdminRole.admin)
