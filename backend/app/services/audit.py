"""
감사 로그 기록 헬퍼.
표준 action: faq.create|faq.update|faq.delete
             doc.upload|doc.approve|doc.delete
             user.restrict|user.unblock
             crawler.approve|crawler.reject
             config.update
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    actor_type: str,  # 'admin_user' | 'system_admin'
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    diff: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        target_type=target_type,
        target_id=target_id,
        diff=diff,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
    return entry
