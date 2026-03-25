from __future__ import annotations

from app.providers.embedding import EmbeddingProvider

import app.providers as providers_module


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    jhgan/ko-sroberta-multitask 기반 로컬 임베딩.
    sentence-transformers 패키지 필요.
    """

    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask"):
        self.model_name = model_name
        self._model = None

    async def warmup(self) -> None:
        """모델 로드. 최초 1회 실행."""
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.model_name)
        providers_module._embedding_warmed_up = True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            await self.warmup()
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return 768
