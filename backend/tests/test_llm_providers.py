"""
LLM Provider 인터페이스 테스트.
"""
import pytest
from app.providers.llm import NullLLMProvider
from app.providers.llm_anthropic import AnthropicLLMProvider, OpenAILLMProvider
from app.providers import get_llm_provider


@pytest.mark.asyncio
async def test_null_provider_always_returns_none():
    provider = NullLLMProvider()
    result = await provider.generate("sys", "user", ["ctx"])
    assert result is None


@pytest.mark.asyncio
async def test_null_provider_returns_none_without_context():
    provider = NullLLMProvider()
    result = await provider.generate("sys", "user", [])
    assert result is None


def test_get_llm_provider_none():
    provider = get_llm_provider({"LLM_PROVIDER": "none"})
    assert isinstance(provider, NullLLMProvider)


def test_get_llm_provider_anthropic():
    provider = get_llm_provider({"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test"})
    assert isinstance(provider, AnthropicLLMProvider)


def test_get_llm_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_llm_provider({"LLM_PROVIDER": "unknown_xyz"})


@pytest.mark.asyncio
async def test_anthropic_provider_no_context_returns_none():
    """근거 없으면 API 호출 없이 None."""
    provider = AnthropicLLMProvider(api_key="test-key")
    result = await provider.generate("sys", "user", context_chunks=[])
    assert result is None


@pytest.mark.asyncio
async def test_anthropic_provider_api_failure_returns_none():
    """API 오류 → None (예외 미전파)."""
    from unittest.mock import patch, AsyncMock
    provider = AnthropicLLMProvider(api_key="invalid-key")

    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
        mock_cls.return_value = mock_client

        result = await provider.generate("sys", "user", context_chunks=["근거"])

    assert result is None
