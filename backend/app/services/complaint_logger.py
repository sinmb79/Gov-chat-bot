"""
민원 이력 DB 저장.
개인정보 원칙: utterance_masked(마스킹), user_key(SHA-256 해시 16자리).
원문 미저장.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import ComplaintLog
from app.services.masking import mask_text, hash_user_key
from app.services.routing import RoutingResult


async def log_complaint(
    db: AsyncSession,
    tenant_id: str,
    raw_utterance: str,
    raw_user_id: str,
    result: RoutingResult,
    channel: str = "kakao",
) -> ComplaintLog:
    """
    민원 이력을 ComplaintLog에 기록.
    - utterance: 마스킹 후 저장
    - user_key: SHA-256 해시 16자리
    - 원문 미저장
    """
    entry = ComplaintLog(
        tenant_id=tenant_id,
        user_key=hash_user_key(raw_user_id),
        utterance_masked=mask_text(raw_utterance)[:1000],
        channel=channel,
        request_id=result.request_id,
        response_tier=result.tier,
        response_source=result.source,
        faq_id=result.faq_id,
        doc_id=result.doc_id,
        response_ms=result.elapsed_ms,
        is_timeout=result.is_timeout,
    )
    db.add(entry)
    await db.commit()
    return entry
