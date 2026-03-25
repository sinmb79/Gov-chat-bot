from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import FAQ
from app.providers.embedding import EmbeddingProvider
from app.providers.vectordb import VectorDBProvider
from app.providers.base import SearchResult

FAQ_SIMILARITY_THRESHOLD = 0.85  # Tier A 기준


class FAQSearchService:
    """
    Tier A — FAQ 임베딩 유사도 검색.
    임베딩 유사도 ≥ 0.85 시 등록 FAQ 반환.
    """

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
        self, tenant_id: str, utterance: str
    ) -> Optional[tuple[FAQ, float]]:
        """
        발화를 임베딩 → 벡터DB 검색 → 0.85 이상이면 FAQ 반환.
        없으면 None.
        """
        try:
            vecs = await self.embedding.embed([utterance])
        except NotImplementedError:
            return None

        query_vec = vecs[0]
        results = await self.vectordb.search(
            tenant_id=tenant_id,
            query_vec=query_vec,
            top_k=1,
            threshold=FAQ_SIMILARITY_THRESHOLD,
        )

        if not results:
            return None

        top: SearchResult = results[0]
        faq_id = top.metadata.get("faq_id")
        if not faq_id:
            return None

        faq = await self._load_faq(tenant_id, faq_id)
        if faq is None:
            return None

        return faq, top.score

    async def _load_faq(self, tenant_id: str, faq_id: str) -> Optional[FAQ]:
        result = await self.db.execute(
            select(FAQ).where(
                FAQ.tenant_id == tenant_id,
                FAQ.id == faq_id,
                FAQ.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def increment_hit(self, faq_id: str) -> None:
        """FAQ hit_count 증가."""
        faq = await self.db.get(FAQ, faq_id)
        if faq:
            faq.hit_count = (faq.hit_count or 0) + 1
            await self.db.commit()

    async def index_faq(self, tenant_id: str, faq: FAQ) -> None:
        """FAQ를 벡터DB에 색인."""
        text = f"{faq.question}\n{faq.answer}"
        try:
            vecs = await self.embedding.embed([text])
        except NotImplementedError:
            return
        await self.vectordb.upsert(
            tenant_id=tenant_id,
            doc_id=faq.id,
            chunks=[text],
            embeddings=vecs,
            metadatas=[{"faq_id": faq.id, "question": faq.question}],
        )
