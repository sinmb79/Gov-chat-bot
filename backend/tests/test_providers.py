import pytest

from app.providers.llm import NullLLMProvider
from app.providers.embedding import NotImplementedEmbeddingProvider
from app.providers import get_llm_provider, get_embedding_provider


@pytest.mark.asyncio
async def test_null_llm_provider_returns_none():
    """NullLLMProvider().generate(...) == None."""
    provider = NullLLMProvider()
    result = await provider.generate("system", "user", [])
    assert result is None


def test_get_llm_provider_none_config():
    """get_llm_provider({'LLM_PROVIDER':'none'}) == NullLLMProvider 인스턴스."""
    provider = get_llm_provider({"LLM_PROVIDER": "none"})
    assert isinstance(provider, NullLLMProvider)


def test_get_llm_provider_unknown_raises():
    """get_llm_provider({'LLM_PROVIDER':'xyz'}) → ValueError."""
    with pytest.raises(ValueError):
        get_llm_provider({"LLM_PROVIDER": "xyz"})


@pytest.mark.asyncio
async def test_not_implemented_embedding_raises_on_embed():
    """NotImplementedEmbeddingProvider().embed(['test']) → NotImplementedError."""
    provider = NotImplementedEmbeddingProvider()
    with pytest.raises(NotImplementedError):
        await provider.embed(["test"])


@pytest.mark.asyncio
async def test_not_implemented_embedding_warmup_is_noop():
    """.warmup() 호출 시 예외 없이 통과."""
    provider = NotImplementedEmbeddingProvider()
    await provider.warmup()  # 예외 없어야 함
