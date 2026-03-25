"""
메트릭 조회 API — viewer 이상.
GET /api/admin/metrics — Tier별 응답 통계 (ComplaintLog 기반, Redis 선택적)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.admin import AdminUser
from app.models.complaint import ComplaintLog

router = APIRouter(prefix="/api/admin/metrics", tags=["admin-metrics"])


@router.get("")
async def get_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    """
    Tier별 응답 통계.
    Redis가 있으면 MetricsCollector, 없으면 DB 집계로 fallback.
    """
    tenant_id = current_user.tenant_id

    # Redis MetricsCollector 우선
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            from app.services.metrics import MetricsCollector
            collector = MetricsCollector(redis)
            overview = await collector.get_overview(tenant_id)
            counts = overview.get("counts", {})
            total = counts.get("total_count", 0)
            return {
                "total_count": total,
                "tier_counts": {
                    "A": counts.get("faq_hit_count", 0),
                    "B": counts.get("rag_hit_count", 0),
                    "C": counts.get("llm_hit_count", 0),
                    "D": counts.get("fallback_count", 0),
                },
                "timeout_count": counts.get("timeout_count", 0),
                "avg_ms": overview.get("avg_ms", 0),
                "p95_ms": overview.get("p95_ms", 0),
            }
        except Exception:
            pass

    # DB fallback: ComplaintLog 집계
    total_result = await db.execute(
        select(func.count()).where(ComplaintLog.tenant_id == tenant_id)
    )
    total = total_result.scalar() or 0

    tier_result = await db.execute(
        select(ComplaintLog.response_tier, func.count())
        .where(ComplaintLog.tenant_id == tenant_id)
        .group_by(ComplaintLog.response_tier)
    )
    tier_counts = {row[0]: row[1] for row in tier_result.all() if row[0]}

    timeout_result = await db.execute(
        select(func.count()).where(
            ComplaintLog.tenant_id == tenant_id,
            ComplaintLog.is_timeout == True,
        )
    )
    timeout_count = timeout_result.scalar() or 0

    return {
        "total_count": total,
        "tier_counts": {
            "A": tier_counts.get("A", 0),
            "B": tier_counts.get("B", 0),
            "C": tier_counts.get("C", 0),
            "D": tier_counts.get("D", 0),
        },
        "timeout_count": timeout_count,
        "avg_ms": 0,
        "p95_ms": 0,
    }
