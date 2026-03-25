"""
Tier C — LLM 기반 재서술 라우팅 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.routing import ResponseRouter
from app.providers.llm import NullLLMProvider
from app.providers.base import SearchResult


def make_doc(doc_id: str) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.filename = "안내문.txt"
    doc.is_active = True
    doc.published_at = datetime(2026, 3, 1)
    return doc


def make_router(embedding=None, vectordb=None, llm=None) -> ResponseRouter:
    providers = {}
    if embedding:
        providers["embedding"] = embedding
    if vectordb:
        providers["vectordb"] = vectordb
    if llm:
        providers["llm"] = llm
    return ResponseRouter(
        tenant_config={
            "phone_number": "031-860-2000",
            "fallback_dept": "민원과",
            "tenant_name": "동두천시",
        },
        providers=providers,
    )


@pytest.mark.asyncio
async def test_tier_c_returns_llm_answer():
    """LLM 활성화 + RAG 근거 있음 → Tier C 반환."""
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

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="여권 발급은 민원과(031-860-2000)에서 신청하시면 됩니다.")

    router = make_router(embedding=embedding, vectordb=vectordb, llm=llm)
    result = await router.route("tenant-1", "여권 어디서 받아요", "user-1", db=db)

    assert result.tier == "C"
    assert result.source == "llm"
    assert "여권" in result.answer


@pytest.mark.asyncio
async def test_tier_c_skipped_when_llm_is_null():
    """NullLLMProvider → Tier C 스킵 → Tier B 또는 D."""
    doc_id = str(uuid4())
    doc = make_doc(doc_id)

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="내용", doc_id=f"{doc_id}_0", score=0.75,
                     metadata={"doc_id": doc_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    llm = NullLLMProvider()  # none 기본값

    router = make_router(embedding=embedding, vectordb=vectordb, llm=llm)
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    # NullLLM → Tier C 스킵 → Tier B (RAG 매칭 있으므로)
    assert result.tier in ("B", "D")
    assert result.tier != "C"


@pytest.mark.asyncio
async def test_tier_c_skipped_when_no_rag_context():
    """RAG 근거 없음 → LLM 미호출 (할루시네이션 방지)."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[])  # 근거 없음

    db = AsyncMock()

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="LLM 답변")

    router = make_router(embedding=embedding, vectordb=vectordb, llm=llm)
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    # 근거 없으면 LLM 미호출 → Tier D
    assert result.tier == "D"
    llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_tier_c_falls_back_to_d_when_llm_fails():
    """LLM 실패(None 반환) → Tier D 폴백."""
    doc_id = str(uuid4())
    doc = make_doc(doc_id)

    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768])

    vectordb = AsyncMock()
    vectordb.search = AsyncMock(return_value=[
        SearchResult(text="내용", doc_id=f"{doc_id}_0", score=0.75,
                     metadata={"doc_id": doc_id})
    ])

    db = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=doc)
    db.execute.return_value = scalar

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=None)  # LLM 실패

    router = make_router(embedding=embedding, vectordb=vectordb, llm=llm)
    result = await router.route("tenant-1", "질문", "user-1", db=db)

    # LLM None → Tier C 없음 → Tier B (RAG 있으므로)
    assert result.tier in ("B", "D")
    assert result.tier != "C"


@pytest.mark.asyncio
async def test_llm_not_called_without_context_chunks():
    """AnthropicLLMProvider: context_chunks 비어있으면 None."""
    from app.providers.llm_anthropic import AnthropicLLMProvider
    provider = AnthropicLLMProvider(api_key="test-key")
    result = await provider.generate("system", "user", context_chunks=[])
    assert result is None
