from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """실패 시 None 반환. 예외 raise 금지."""
        ...


class NullLLMProvider(LLMProvider):
    """LLM_PROVIDER=none 기본값"""

    async def generate(
        self,
        system_prompt: str = "",
        user_message: str = "",
        context_chunks: list = None,
        max_tokens: int = 512,
    ) -> None:
        return None
