"""
Tier A 라우팅 통합 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.routing import ResponseRouter, RoutingResult
from app.providers.base import SearchResult


def make_router(embedding=None, vectordb=None) -> ResponseRouter:
    providers = {}
    if embedding:
        providers["embedding"] = embedding
    if vectordb:
        providers["vectordb"] = vectordb
    return ResponseRouter(
        tenant_config={
            "phone_number": "031-860-2000",
            "fallback_dept": "민원과",
            "tenant_name": "동두천시",
        },
        providers=providers,
    )


@pytest.mark.asyncio
async def test_tier_a_returns_when_faq_found():
    """벡터DB에서 FAQ 매칭 → Tier A 반환."""
    faq_id = str(uuid4())
    faq = MagicMock()
    faq.id = faq_id
    faq.answer = "여권은 민원과에서 발급합니다."
    faq.question = "여권 발급 방법"
    faq.is_active = True
    faq.hit_count = 0
    faq.updated_at = None

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="여권 발급 방법\n여권은 민원과에서 발급합니다.",
                     doc_id=f"{faq_id}_0", score=0.92, metadata={"faq_id": faq_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=faq)
    db.execute.return_value = scalar
    db.get = AsyncMock(return_value=faq)
    db.commit = AsyncMock()

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "여권 발급 방법", "user-1", db=db)

    assert result.tier == "A"
    assert result.source == "faq"
    assert result.answer == faq.answer


@pytest.mark.asyncio
async def test_tier_a_skipped_when_no_match():
    """매칭 없으면 Tier D 반환."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])  # 빈 결과

    db = AsyncMock()

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "모르는 질문", "user-1", db=db)

    assert result.tier == "D"
    assert result.source == "fallback"


@pytest.mark.asyncio
async def test_routing_result_has_faq_id():
    """Tier A 결과에 faq_id가 포함된다."""
    faq_id = str(uuid4())
    faq = MagicMock()
    faq.id = faq_id
    faq.answer = "답변"
    faq.question = "질문"
    faq.is_active = True
    faq.hit_count = 0
    faq.updated_at = None

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="Q\nA", doc_id=f"{faq_id}_0", score=0.90,
                     metadata={"faq_id": faq_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=faq)
    db.execute.return_value = scalar
    db.get = AsyncMock(return_value=faq)
    db.commit = AsyncMock()

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    assert result.faq_id == faq_id


@pytest.mark.asyncio
async def test_routing_result_tier_d_has_fallback_info():
    """Tier D 결과에 담당부서·전화번호가 포함된다."""
    router = make_router()
    result = await router.route("tenant-1", "알 수 없는 질문", "user-1", db=None)

    assert result.tier == "D"
    assert "031-860-2000" in result.answer
    assert "민원과" in result.answer


@pytest.mark.asyncio
async def test_timeout_returns_tier_d_is_timeout():
    """타임아웃 발생 시 Tier D + is_timeout=True."""
    import asyncio

    async def slow_embed(texts):
        await asyncio.sleep(10)  # 타임아웃보다 긴 대기
        return [[0.0] * 768]

    embedding = AsyncMock()
    embedding.embed = AsyncMock(side_effect=slow_embed)

    vectordb = AsyncMock()

    # 타임아웃을 매우 짧게 설정
    router = make_router(embedding=embedding, vectordb=vectordb)
    router.TIMEOUT_MS = 50  # 50ms

    db = AsyncMock()
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    assert result.tier == "D"
    assert result.is_timeout is True
