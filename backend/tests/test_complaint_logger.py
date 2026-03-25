"""
민원 이력 저장 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.complaint_logger import log_complaint
from app.services.routing import RoutingResult


def make_result(tier="D", source="fallback", request_id="req-1") -> RoutingResult:
    return RoutingResult(
        answer="답변",
        tier=tier,
        source=source,
        elapsed_ms=100,
        is_timeout=False,
        request_id=request_id,
    )


@pytest.mark.asyncio
async def test_log_complaint_masks_utterance():
    """민원 이력에 원문 미저장, 마스킹 후 저장."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    raw_utterance = "제 전화번호는 010-1234-5678 입니다"
    result = make_result()

    entry = await log_complaint(
        db=db,
        tenant_id="t1",
        raw_utterance=raw_utterance,
        raw_user_id="kakao-user-123",
        result=result,
    )

    # 원문 미저장
    assert "010-1234-5678" not in (entry.utterance_masked or "")
    # 마스킹 처리됨
    assert "***-****-****" in (entry.utterance_masked or "")


@pytest.mark.asyncio
async def test_log_complaint_hashes_user_id():
    """user_key는 해시값(16자리)으로 저장."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    result = make_result()
    entry = await log_complaint(
        db=db,
        tenant_id="t1",
        raw_utterance="일반 민원",
        raw_user_id="real-kakao-id-12345",
        result=result,
    )

    assert entry.user_key != "real-kakao-id-12345"
    assert len(entry.user_key) == 16


@pytest.mark.asyncio
async def test_log_complaint_stores_tier_and_source():
    """response_tier, response_source 저장."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    result = make_result(tier="A", source="faq")
    entry = await log_complaint(
        db=db,
        tenant_id="t1",
        raw_utterance="질문",
        raw_user_id="user-1",
        result=result,
    )

    assert entry.response_tier == "A"
    assert entry.response_source == "faq"


@pytest.mark.asyncio
async def test_log_complaint_stores_request_id():
    """request_id 저장 (Idempotency 추적)."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    result = make_result(request_id="unique-req-abc")
    entry = await log_complaint(
        db=db,
        tenant_id="t1",
        raw_utterance="질문",
        raw_user_id="user-1",
        result=result,
    )

    assert entry.request_id == "unique-req-abc"


@pytest.mark.asyncio
async def test_log_complaint_timeout_flag():
    """타임아웃 시 is_timeout=True 저장."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    result = RoutingResult(
        answer="타임아웃",
        tier="D",
        source="fallback",
        elapsed_ms=4500,
        is_timeout=True,
    )

    entry = await log_complaint(
        db=db,
        tenant_id="t1",
        raw_utterance="질문",
        raw_user_id="user-1",
        result=result,
    )

    assert entry.is_timeout is True
