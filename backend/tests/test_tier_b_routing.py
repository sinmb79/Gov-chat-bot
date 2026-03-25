"""
Tier B RAG 라우팅 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.routing import ResponseRouter
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


def make_doc(doc_id: str) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.filename = "안내문.txt"
    doc.is_active = True
    doc.published_at = datetime(2026, 3, 1)
    return doc


@pytest.mark.asyncio
async def test_tier_b_returns_when_doc_found():
    """문서 RAG 매칭 → Tier B 반환."""
    doc_id = str(uuid4())
    doc = make_doc(doc_id)

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="여권은 민원과에서 발급합니다.", doc_id=f"{doc_id}_0",
                     score=0.75, metadata={"doc_id": doc_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "여권 발급 방법", "user-1", db=db)

    assert result.tier == "B"
    assert result.source == "rag"


@pytest.mark.asyncio
async def test_tier_b_skipped_when_no_doc_match():
    """문서 매칭 없으면 Tier D."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])

    db = AsyncMock()

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "모르는 질문", "user-1", db=db)

    assert result.tier == "D"


@pytest.mark.asyncio
async def test_tier_b_result_has_doc_name():
    """Tier B 결과에 doc_name 포함."""
    doc_id = str(uuid4())
    doc = make_doc(doc_id)

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="내용", doc_id=f"{doc_id}_0", score=0.72,
                     metadata={"doc_id": doc_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    router = make_router(embedding=embedding, vectordb=vectordb)
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    assert result.doc_name is not None


@pytest.mark.asyncio
async def test_tier_a_takes_priority_over_tier_b():
    """FAQ 유사도 ≥ 0.85 → Tier A (Tier B 미실행)."""
    faq_id = str(uuid4())
    faq = MagicMock()
    faq.id = faq_id
    faq.answer = "FAQ 답변"
    faq.question = "질문"
    faq.is_active = True
    faq.hit_count = 0
    faq.updated_at = None

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    # FAQ 검색: 높은 유사도
    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="Q\nA", doc_id=f"{faq_id}_0", score=0.92,
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

    # FAQ가 먼저 매칭되면 Tier A
    assert result.tier == "A"
