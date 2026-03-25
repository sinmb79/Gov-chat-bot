from app.providers.llm import LLMProvider, NullLLMProvider
from app.providers.embedding import EmbeddingProvider, NotImplementedEmbeddingProvider
from app.providers.vectordb import VectorDBProvider

# 워밍업 상태 전역 플래그
_embedding_warmed_up = False


def get_llm_provider(config: dict) -> LLMProvider:
    provider = config.get("LLM_PROVIDER", "none")
    if provider == "none":
        return NullLLMProvider()
    if provider == "anthropic":
        from app.providers.llm_anthropic import AnthropicLLMProvider
        return AnthropicLLMProvider(
            api_key=config.get("ANTHROPIC_API_KEY", ""),
            model=config.get("LLM_MODEL", "claude-haiku-4-5-20251001"),
        )
    if provider == "openai":
        from app.providers.llm_anthropic import OpenAILLMProvider
        return OpenAILLMProvider(
            api_key=config.get("OPENAI_API_KEY", ""),
            model=config.get("LLM_MODEL", "gpt-4o-mini"),
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def get_embedding_provider(config: dict) -> EmbeddingProvider:
    provider = config.get("EMBEDDING_PROVIDER", "none")
    if provider == "local":
        from app.providers.local_embedding import LocalEmbeddingProvider
        model = config.get("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        return LocalEmbeddingProvider(model_name=model)
    return NotImplementedEmbeddingProvider()


def get_vectordb_provider(config: dict) -> VectorDBProvider:
    from app.providers.chroma import ChromaVectorDBProvider
    return ChromaVectorDBProvider(
        host=config.get("CHROMA_HOST", "chromadb"),
        port=int(config.get("CHROMA_PORT", 8000)),
    )
