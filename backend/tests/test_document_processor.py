"""
DocumentProcessor + 텍스트 파서 단위 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.parsers.text_parser import extract_text, chunk_text
from app.services.document_processor import DocumentProcessor


# ── 파서 테스트 ─────────────────────────────────────────────────────

def test_extract_text_txt():
    content = "안녕하세요\n여권 발급 안내입니다".encode("utf-8")
    result = extract_text(content, "guide.txt")
    assert "여권" in result


def test_extract_text_md():
    content = "# 제목\n본문 내용".encode("utf-8")
    result = extract_text(content, "readme.md")
    assert "본문" in result


def test_extract_text_html():
    content = "<html><body><p>여권 안내</p><script>alert(1)</script></body></html>".encode("utf-8")
    result = extract_text(content, "page.html")
    assert "여권" in result
    assert "alert" not in result


def test_extract_text_unsupported_returns_none():
    result = extract_text(b"binary", "file.exe")
    assert result is None


def test_chunk_text_splits_correctly():
    text = "\n".join(["문장 " + str(i) for i in range(50)])
    chunks = chunk_text(text, chunk_size=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 0


def test_chunk_text_small_text_single_chunk():
    text = "짧은 텍스트"
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert "짧은 텍스트" in chunks[0]


# ── DocumentProcessor 테스트 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_processor_stores_chunks_in_vectordb():
    """파싱 성공 → VectorDB에 upsert 호출."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])

    vectordb = AsyncMock()
    vectordb.upsert = AsyncMock(return_value=2)

    db = AsyncMock()
    db.commit = AsyncMock()

    doc = MagicMock()
    doc.id = "doc-1"
    doc.filename = "test.txt"
    doc.published_at = None
    doc.status = "pending"
    doc.chunk_count = 0

    processor = DocumentProcessor(embedding, vectordb, db)
    content = "첫 번째 문단입니다.\n두 번째 문단입니다.".encode("utf-8")
    count = await processor.process("tenant-1", doc, content)

    assert count > 0
    assert vectordb.upsert.called
    assert doc.status == "processed"


@pytest.mark.asyncio
async def test_processor_fails_on_unsupported_format():
    """지원하지 않는 파일 형식 → chunk_count=0, status=parse_failed."""
    embedding = AsyncMock()
    vectordb = AsyncMock()
    db = AsyncMock()
    db.commit = AsyncMock()

    doc = MagicMock()
    doc.id = "doc-2"
    doc.filename = "file.exe"
    doc.published_at = None
    doc.status = "pending"

    processor = DocumentProcessor(embedding, vectordb, db)
    count = await processor.process("tenant-1", doc, b"binary data")

    assert count == 0
    assert doc.status == "parse_failed"


@pytest.mark.asyncio
async def test_processor_handles_embedding_not_implemented():
    """임베딩 미구성 → status=embedding_unavailable."""
    embedding = AsyncMock()
    embedding.embed = AsyncMock(side_effect=NotImplementedError)

    vectordb = AsyncMock()
    db = AsyncMock()
    db.commit = AsyncMock()

    doc = MagicMock()
    doc.id = "doc-3"
    doc.filename = "guide.txt"
    doc.published_at = None
    doc.status = "pending"

    processor = DocumentProcessor(embedding, vectordb, db)
    count = await processor.process("tenant-1", doc, "본문 내용".encode("utf-8"))

    assert count == 0
    assert doc.status == "embedding_unavailable"
