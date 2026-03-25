"""
RAGSearchService 단위 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.rag_search import RAGSearchService, RAG_SIMILARITY_THRESHOLD
from app.providers.base import SearchResult


def make_doc(tenant_id: str, filename: str = "안내문.txt") -> MagicMock:
    doc = MagicMock()
    doc.id = str(uuid4())
    doc.tenant_id = tenant_id
    doc.filename = filename
    doc.is_active = True
    doc.published_at = datetime(2026, 3, 1)
    return doc


@pytest.mark.asyncio
async def test_rag_search_returns_results_above_threshold():
    """유사도 ≥ 0.70 → RAGSearchResult 반환."""
    doc = make_doc("t1")
    doc_id = doc.id

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(
            text="여권은 민원과에서 발급합니다.",
            doc_id=f"{doc_id}_0",
            score=0.78,
            metadata={"doc_id": doc_id, "filename": "여권안내.txt"},
        )
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    service = RAGSearchService(embedding, vectordb, db)
    results = await service.search("t1", "여권 발급")

    assert results is not None
    assert len(results) > 0
    assert results[0].score >= RAG_SIMILARITY_THRESHOLD


@pytest.mark.asyncio
async def test_rag_search_returns_none_when_no_match():
    """매칭 없으면 None."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])

    db = AsyncMock()

    service = RAGSearchService(embedding, vectordb, db)
    results = await service.search("t1", "알 수 없는 질문")

    assert results is None


@pytest.mark.asyncio
async def test_rag_search_excludes_inactive_docs():
    """is_active=False 문서 → 결과에서 제외."""
    doc_id = str(uuid4())

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="내용", doc_id=f"{doc_id}_0", score=0.85,
                     metadata={"doc_id": doc_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=None)  # is_active 필터로 None
    db.execute.return_value = scalar

    service = RAGSearchService(embedding, vectordb, db)
    results = await service.search("t1", "질문")

    assert results is None


def test_rag_build_answer_includes_citation():
    """응답에 출처(문서명·날짜) 포함."""
    doc = make_doc("t1", "여권발급안내.txt")

    embedding = AsyncMock()
    vectordb = AsyncMock()
    db = AsyncMock()

    from app.services.rag_search import RAGSearchResult
    rag_result = RAGSearchResult(
        chunk_text="여권 발급은 민원과에서 처리합니다.",
        doc=doc,
        score=0.78,
    )

    service = RAGSearchService(embedding, vectordb, db)
    answer = service.build_answer("여권 질문", [rag_result])

    assert "출처" in answer
    assert "여권발급안내.txt" in answer


@pytest.mark.asyncio
async def test_rag_deduplicates_same_doc_chunks():
    """같은 문서의 여러 청크 → 최고 점수 1개만."""
    doc_id = str(uuid4())
    doc = make_doc("t1")
    doc.id = doc_id

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="청크1", doc_id=f"{doc_id}_0", score=0.80,
                     metadata={"doc_id": doc_id}),
        SearchResult(text="청크2", doc_id=f"{doc_id}_1", score=0.75,
                     metadata={"doc_id": doc_id}),
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    service = RAGSearchService(embedding, vectordb, db)
    results = await service.search("t1", "질문")

    # 같은 문서는 1개만
    doc_ids = [r.doc.id for r in results]
    assert len(doc_ids) == len(set(doc_ids))
