"""
FAQSearchService 단위 테스트.
임베딩/벡터DB는 Mock 사용.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.faq_search import FAQSearchService, FAQ_SIMILARITY_THRESHOLD
from app.providers.base import SearchResult


def make_faq(tenant_id: str, question: str = "Q", answer: str = "A") -> MagicMock:
    faq = MagicMock()
    faq.id = str(uuid4())
    faq.tenant_id = tenant_id
    faq.question = question
    faq.answer = answer
    faq.is_active = True
    faq.hit_count = 0
    faq.updated_at = None
    return faq


@pytest.mark.asyncio
async def test_faq_search_above_threshold_returns_faq():
    """유사도 ≥ 0.85 → FAQ 반환."""
    faq = make_faq("t1")
    faq_id = faq.id

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="Q\nA", doc_id=f"{faq_id}_0", score=0.92, metadata={"faq_id": faq_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=faq)
    db.execute.return_value = scalar

    service = FAQSearchService(embedding, vectordb, db)
    result = await service.search("t1", "여권 발급")

    assert result is not None
    found_faq, score = result
    assert found_faq.id == faq_id
    assert score >= FAQ_SIMILARITY_THRESHOLD


@pytest.mark.asyncio
async def test_faq_search_below_threshold_returns_none():
    """유사도 < 0.85 → None 반환."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])  # threshold 미달로 빈 결과

    db = AsyncMock()

    service = FAQSearchService(embedding, vectordb, db)
    result = await service.search("t1", "모르는 질문")

    assert result is None


@pytest.mark.asyncio
async def test_faq_search_tenant_isolation():
    """다른 테넌트의 FAQ가 반환되지 않는다."""
    faq_tenant_b = make_faq("tenant-B")
    faq_id = faq_tenant_b.id

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="Q\nA", doc_id=f"{faq_id}_0", score=0.95, metadata={"faq_id": faq_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    # tenant-A로 조회하면 None (다른 테넌트 FAQ)
    scalar.scalar_one_or_none = MagicMock(return_value=None)
    db.execute.return_value = scalar

    service = FAQSearchService(embedding, vectordb, db)
    result = await service.search("tenant-A", "테스트 질문")  # tenant-A로 검색

    assert result is None


@pytest.mark.asyncio
async def test_faq_search_hit_count_increment():
    """FAQ 검색 성공 시 hit_count가 증가한다."""
    faq = make_faq("t1")
    faq.hit_count = 5

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="Q\nA", doc_id=f"{faq.id}_0", score=0.90,
                     metadata={"faq_id": faq.id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=faq)
    db.execute.return_value = scalar
    db.get = AsyncMock(return_value=faq)
    db.commit = AsyncMock()

    service = FAQSearchService(embedding, vectordb, db)
    result = await service.search("t1", "질문")
    assert result is not None

    await service.increment_hit(faq.id)
    assert faq.hit_count == 6


@pytest.mark.asyncio
async def test_faq_search_embedding_not_implemented_returns_none():
    """EmbeddingProvider가 NotImplementedError → None 반환 (graceful)."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(side_effect=NotImplementedError("not configured"))

    vectordb = AsyncMock()
    db = AsyncMock()

    service = FAQSearchService(embedding, vectordb, db)
    result = await service.search("t1", "질문")

    assert result is None
