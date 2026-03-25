from typing import Optional

from app.providers.base import SearchResult
from app.providers.vectordb import VectorDBProvider


class ChromaVectorDBProvider(VectorDBProvider):
    """
    ChromaDB 기반 벡터 검색.
    컬렉션명 = tenant_{tenant_id} (테넌트 격리)
    """

    def __init__(self, host: str = "chromadb", port: int = 8000):
        self.host = host
        self.port = port
        self._client = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.HttpClient(host=self.host, port=self.port)
        return self._client

    def _collection_name(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    async def upsert(
        self,
        tenant_id: str,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> int:
        client = self._get_client()
        collection = client.get_or_create_collection(self._collection_name(tenant_id))
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
        return len(chunks)

    async def search(
        self,
        tenant_id: str,
        query_vec: list[float],
        top_k: int = 3,
        threshold: float = 0.70,
    ) -> list[SearchResult]:
        client = self._get_client()
        collection_name = self._collection_name(tenant_id)
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            return []

        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if not results["ids"] or not results["ids"][0]:
            return []

        for i, doc_id in enumerate(results["ids"][0]):
            # Chroma distances: 1 - cosine_similarity (낮을수록 유사)
            distance = results["distances"][0][i]
            score = 1.0 - distance  # cosine similarity로 변환
            if score >= threshold:
                search_results.append(
                    SearchResult(
                        text=results["documents"][0][i],
                        doc_id=doc_id,
                        score=score,
                        metadata=results["metadatas"][0][i] or {},
                    )
                )
        return search_results

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        client = self._get_client()
        collection_name = self._collection_name(tenant_id)
        try:
            collection = client.get_collection(collection_name)
            # doc_id로 시작하는 모든 청크 삭제
            all_ids = collection.get()["ids"]
            ids_to_delete = [id_ for id_ in all_ids if id_.startswith(f"{doc_id}_")]
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
        except Exception:
            pass
