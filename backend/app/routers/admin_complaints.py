"""
민원 이력 조회 API — viewer 이상.
GET /api/admin/complaints — 민원 이력 목록 (마스킹 상태로 노출)
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.admin import AdminUser
from app.models.complaint import ComplaintLog

router = APIRouter(prefix="/api/admin/complaints", tags=["admin-complaints"])


class ComplaintOut(BaseModel):
    id: str
    user_key: str          # 해시값만 노출
    utterance_masked: Optional[str] = None  # 마스킹된 발화
    channel: Optional[str] = None
    response_tier: Optional[str] = None
    response_source: Optional[str] = None
    response_ms: Optional[int] = None
    is_timeout: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[ComplaintOut])
async def list_complaints(
    limit: int = Query(default=50, le=200),
    tier: Optional[str] = Query(default=None, description="A|B|C|D"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    """
    민원 이력 조회.
    - utterance는 마스킹 상태로만 노출 (관리자도 원문 열람 불가)
    - user_key는 해시값만 노출
    """
    query = (
        select(ComplaintLog)
        .where(ComplaintLog.tenant_id == current_user.tenant_id)
        .order_by(desc(ComplaintLog.created_at))
        .limit(limit)
    )
    if tier:
        query = query.where(ComplaintLog.response_tier == tier)

    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        ComplaintOut(
            id=log.id,
            user_key=log.user_key or "",
            utterance_masked=log.utterance_masked,
            channel=log.channel,
            response_tier=log.response_tier,
            response_source=log.response_source,
            response_ms=log.response_ms,
            is_timeout=bool(log.is_timeout),
            created_at=log.created_at,
        )
        for log in logs
    ]
