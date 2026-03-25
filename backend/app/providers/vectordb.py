from abc import ABC, abstractmethod

from app.providers.base import SearchResult


class VectorDBProvider(ABC):
    @abstractmethod
    async def upsert(
        self,
        tenant_id: str,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> int:
        ...

    @abstractmethod
    async def search(
        self,
        tenant_id: str,
        query_vec: list[float],
        top_k: int = 3,
        threshold: float = 0.70,
    ) -> list[SearchResult]:
        ...

    @abstractmethod
    async def delete(self, tenant_id: str, doc_id: str) -> None:
        ...
