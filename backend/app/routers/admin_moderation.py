"""
악성 유저 관리 API — 편집장(editor) 이상.
GET    /api/admin/moderation                    — 제한 유저 목록
POST   /api/admin/moderation/{user_key}/release — 수동 해제
POST   /api/admin/moderation/{user_key}/escalate — 수동 레벨 상승
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_editor, require_admin
from app.models.admin import AdminUser
from app.models.moderation import UserRestriction
from app.services.moderation import ModerationService
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/moderation", tags=["admin-moderation"])


class RestrictionOut(BaseModel):
    id: str
    user_key: str
    level: int
    reason: str | None = None
    auto_applied: bool
    expires_at: str | None = None

    class Config:
        from_attributes = True


class EscalateRequest(BaseModel):
    reason: str = "수동 조치"


@router.get("", response_model=list[RestrictionOut])
async def list_restrictions(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """제한(level ≥ 1) 유저 목록."""
    result = await db.execute(
        select(UserRestriction).where(
            UserRestriction.tenant_id == current_user.tenant_id,
            UserRestriction.level > 0,
        )
    )
    restrictions = result.scalars().all()
    return [
        RestrictionOut(
            id=r.id,
            user_key=r.user_key,
            level=r.level,
            reason=r.reason,
            auto_applied=r.auto_applied,
            expires_at=r.expires_at.isoformat() if r.expires_at else None,
        )
        for r in restrictions
    ]


@router.post("/{user_key}/release")
async def release_restriction(
    user_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """수동 해제 (Level 4+ 포함)."""
    service = ModerationService(db)
    await service.release(current_user.tenant_id, user_key, current_user.id)

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="user.unblock",
        target_type="user_restriction",
        diff={"user_key": user_key},
    )
    return {"user_key": user_key, "released": True}


@router.post("/{user_key}/escalate")
async def escalate_restriction(
    user_key: str,
    body: EscalateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """수동 레벨 상승."""
    service = ModerationService(db)
    new_level = await service.escalate(current_user.tenant_id, user_key, body.reason)

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="user.restrict",
        target_type="user_restriction",
        diff={"user_key": user_key, "new_level": new_level, "reason": body.reason},
    )
    return {"user_key": user_key, "new_level": new_level}
