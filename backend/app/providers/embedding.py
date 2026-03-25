from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def warmup(self) -> None:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...


class NotImplementedEmbeddingProvider(EmbeddingProvider):
    """Phase 1에서 LocalEmbeddingProvider로 교체 예정"""

    async def embed(self, texts: list[str]) -> list:
        raise NotImplementedError("Embedding provider not configured. Set EMBEDDING_PROVIDER.")

    async def warmup(self) -> None:
        pass  # 예외 없이 통과

    @property
    def dimension(self) -> int:
        return 768
