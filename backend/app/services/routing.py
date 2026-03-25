import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoutingResult:
    answer: str
    tier: str  # 'A'|'B'|'C'|'D'
    source: str  # 'faq'|'rag'|'llm'|'fallback'
    faq_id: Optional[str] = None
    doc_id: Optional[str] = None
    doc_name: Optional[str] = None
    doc_date: Optional[str] = None
    score: float = 0.0
    elapsed_ms: int = 0
    is_timeout: bool = False
    request_id: Optional[str] = None

    def to_dict(self) -> dict:
        citations = []
        if self.doc_name:
            citations.append({"doc": self.doc_name, "date": self.doc_date or ""})
        return {
            "answer": self.answer,
            "tier": self.tier,
            "source": self.source,
            "faq_id": self.faq_id,
            "doc_id": self.doc_id,
            "score": self.score,
            "elapsed_ms": self.elapsed_ms,
            "is_timeout": self.is_timeout,
            "request_id": self.request_id,
            "citations": citations,
        }


class ResponseRouter:
    TIMEOUT_MS = 4500  # 4.5초 — 카카오 5초 한계 - 500ms

    def __init__(self, tenant_config: dict, providers: dict):
        self.tenant_config = tenant_config
        self.providers = providers

    async def route(
        self,
        tenant_id: str,
        utterance: str,
        user_key: str,
        request_id: Optional[str] = None,
        db=None,
    ) -> RoutingResult:
        import time
        start = time.monotonic()
        try:
            return await asyncio.wait_for(
                self._try_tiers(tenant_id, utterance, user_key, request_id, db, start),
                timeout=self.TIMEOUT_MS / 1000,
            )
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            return self._tier_d(tenant_id, elapsed, is_timeout=True, request_id=request_id)

    async def _try_tiers(
        self,
        tenant_id: str,
        utterance: str,
        user_key: str,
        request_id: Optional[str],
        db,
        start: float,
    ) -> RoutingResult:
        import time

        # Tier A — FAQ 임베딩 유사도 검색
        tier_a = await self._try_tier_a(tenant_id, utterance, db)
        if tier_a is not None:
            tier_a.elapsed_ms = int((time.monotonic() - start) * 1000)
            tier_a.request_id = request_id
            return tier_a

        # Tier C — LLM 기반 재서술 (RAG 근거 있음 + LLM 활성화)
        # Tier B보다 먼저 시도: LLM 활성 시 템플릿 대신 재서술
        tier_c = await self._try_tier_c(tenant_id, utterance, db)
        if tier_c is not None:
            tier_c.elapsed_ms = int((time.monotonic() - start) * 1000)
            tier_c.request_id = request_id
            return tier_c

        # Tier B — RAG 문서 검색 (LLM 비활성 또는 Tier C 실패 시)
        tier_b = await self._try_tier_b(tenant_id, utterance, db)
        if tier_b is not None:
            tier_b.elapsed_ms = int((time.monotonic() - start) * 1000)
            tier_b.request_id = request_id
            return tier_b

        elapsed = int((time.monotonic() - start) * 1000)
        return self._tier_d(tenant_id, elapsed, request_id=request_id)

    async def _try_tier_a(self, tenant_id: str, utterance: str, db) -> Optional[RoutingResult]:
        """Tier A — FAQ 임베딩 유사도 ≥ 0.85."""
        embedding_provider = self.providers.get("embedding")
        vectordb_provider = self.providers.get("vectordb")

        if embedding_provider is None or vectordb_provider is None or db is None:
            return None

        from app.services.faq_search import FAQSearchService
        service = FAQSearchService(embedding_provider, vectordb_provider, db)
        match = await service.search(tenant_id, utterance)

        if match is None:
            return None

        faq, score = match
        # hit_count 비동기 증가 (fire-and-forget)
        await service.increment_hit(faq.id)

        citation_date = (
            faq.updated_at.strftime("%Y.%m") if faq.updated_at else ""
        )

        return RoutingResult(
            answer=faq.answer,
            tier="A",
            source="faq",
            faq_id=faq.id,
            doc_name=f"FAQ: {faq.question[:30]}",
            doc_date=citation_date,
            score=score,
        )

    async def _try_tier_c(self, tenant_id: str, utterance: str, db) -> Optional[RoutingResult]:
        """Tier C — RAG 근거 있음 + LLM 활성화 → 근거 기반 재서술."""
        llm_provider = self.providers.get("llm")
        embedding_provider = self.providers.get("embedding")
        vectordb_provider = self.providers.get("vectordb")

        if llm_provider is None or embedding_provider is None or vectordb_provider is None or db is None:
            return None

        # NullLLMProvider → None 즉시 반환
        from app.providers.llm import NullLLMProvider
        if isinstance(llm_provider, NullLLMProvider):
            return None

        # RAG 검색 (Tier B와 동일 임계값)
        from app.services.rag_search import RAGSearchService
        rag_service = RAGSearchService(embedding_provider, vectordb_provider, db)
        rag_results = await rag_service.search(tenant_id, utterance)

        if not rag_results:
            return None  # 근거 없으면 LLM 미호출 (P6 할루시네이션 방지)

        # 근거 기반 LLM 재서술
        context_chunks = [r.chunk_text for r in rag_results[:3]]
        context_str = "\n---\n".join(context_chunks)
        tenant_name = self.tenant_config.get("tenant_name", "담당 기관")

        system_prompt = (
            f"당신은 {tenant_name}의 민원 안내 AI입니다.\n"
            f"반드시 아래 근거 문서의 내용만을 바탕으로 답변하세요.\n"
            f"근거 없는 내용은 절대 추측하지 마세요.\n\n"
            f"근거 문서:\n{context_str}"
        )

        answer = await llm_provider.generate(
            system_prompt=system_prompt,
            user_message=utterance,
            context_chunks=context_chunks,
        )

        if answer is None:
            return None  # LLM 실패 → Tier D로 폴백

        best = rag_results[0]
        return RoutingResult(
            answer=answer,
            tier="C",
            source="llm",
            doc_id=best.doc.id,
            doc_name=best.doc_name,
            doc_date=best.doc_date,
            score=best.score,
        )

    async def _try_tier_b(self, tenant_id: str, utterance: str, db) -> Optional[RoutingResult]:
        """Tier B — RAG 유사도 ≥ 0.70 + 근거 문서 존재."""
        embedding_provider = self.providers.get("embedding")
        vectordb_provider = self.providers.get("vectordb")

        if embedding_provider is None or vectordb_provider is None or db is None:
            return None

        from app.services.rag_search import RAGSearchService
        service = RAGSearchService(embedding_provider, vectordb_provider, db)
        results = await service.search(tenant_id, utterance)

        if not results:
            return None

        best = results[0]
        answer = service.build_answer(utterance, results)

        return RoutingResult(
            answer=answer,
            tier="B",
            source="rag",
            doc_id=best.doc.id,
            doc_name=best.doc_name,
            doc_date=best.doc_date,
            score=best.score,
        )

    def _tier_d(
        self,
        tenant_id: str,
        elapsed_ms: int,
        is_timeout: bool = False,
        request_id: Optional[str] = None,
    ) -> RoutingResult:
        # DB 조회 없이 tenant_config 메모리에서 직접 읽음 (~5ms)
        phone = self.tenant_config.get("phone_number", "대표번호")
        dept = self.tenant_config.get("fallback_dept", "담당부서")
        name = self.tenant_config.get("tenant_name", "해당 기관")

        answer = f"해당 민원은 {name} {dept}({phone})로 문의해주세요."
        return RoutingResult(
            answer=answer,
            tier="D",
            source="fallback",
            elapsed_ms=elapsed_ms,
            is_timeout=is_timeout,
            request_id=request_id,
        )
