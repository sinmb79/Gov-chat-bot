"""
Tier B — RAG 검색.
임베딩 유사도 ≥ 0.70 + 근거 문서 존재 → 문서 기반 템플릿 응답.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document
from app.providers.base import SearchResult
from app.providers.embedding import EmbeddingProvider
from app.providers.vectordb import VectorDBProvider

RAG_SIMILARITY_THRESHOLD = 0.70  # Tier B 기준


class RAGSearchResult:
    def __init__(self, chunk_text: str, doc: Document, score: float):
        self.chunk_text = chunk_text
        self.doc = doc
        self.score = score

    @property
    def doc_name(self) -> str:
        return self.doc.filename

    @property
    def doc_date(self) -> str:
        if self.doc.published_at:
            return self.doc.published_at.strftime("%Y.%m")
        return ""


class RAGSearchService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vectordb_provider: VectorDBProvider,
        db: AsyncSession,
    ):
        self.embedding = embedding_provider
        self.vectordb = vectordb_provider
        self.db = db

    async def search(
        self, tenant_id: str, utterance: str, top_k: int = 3
    ) -> Optional[list[RAGSearchResult]]:
        """
        발화를 임베딩 → 벡터DB 검색 → 0.70 이상 문서 청크 반환.
        결과 없으면 None.
        """
        try:
            vecs = await self.embedding.embed([utterance])
        except NotImplementedError:
            return None

        query_vec = vecs[0]
        results = await self.vectordb.search(
            tenant_id=tenant_id,
            query_vec=query_vec,
            top_k=top_k,
            threshold=RAG_SIMILARITY_THRESHOLD,
        )

        if not results:
            return None

        # 중복 doc_id 제거 (같은 문서의 여러 청크 중 최고 점수만)
        seen_docs: dict[str, SearchResult] = {}
        for r in results:
            doc_id = r.metadata.get("doc_id", r.doc_id.rsplit("_", 1)[0])
            if doc_id not in seen_docs or r.score > seen_docs[doc_id].score:
                seen_docs[doc_id] = r

        # Document 레코드 로드 (is_active=True만)
        rag_results = []
        for doc_id, sr in seen_docs.items():
            doc = await self._load_doc(tenant_id, doc_id)
            if doc:
                rag_results.append(RAGSearchResult(sr.text, doc, sr.score))

        return rag_results if rag_results else None

    async def _load_doc(self, tenant_id: str, doc_id: str) -> Optional[Document]:
        result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.id == doc_id,
                Document.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def build_answer(self, utterance: str, rag_results: list[RAGSearchResult]) -> str:
        """
        문서 기반 템플릿 응답 생성.
        출처 2단계 포맷 (간단형).
        """
        # 근거 문단 합치기 (최대 2개)
        contexts = [r.chunk_text[:300] for r in rag_results[:2]]
        context_str = "\n---\n".join(contexts)

        best = rag_results[0]
        citation = f"📎 출처: {best.doc_name}"
        if best.doc_date:
            citation += f" ({best.doc_date})"

        return f"{context_str}\n\n{citation}"
