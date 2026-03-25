from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 보안
    SECRET_KEY: str = "change-this-in-production-32chars"
    JWT_EXPIRE_HOURS: int = 24

    # 데이터베이스
    DATABASE_URL: str = "postgresql+asyncpg://botuser:botpass@db:5432/smartbot"
    REDIS_URL: str = "redis://redis:6379"

    # 벡터DB
    VECTOR_DB: str = "chromadb"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

    # Provider 기본값 (테넌트별 TenantConfig로 오버라이드 가능)
    LLM_PROVIDER: str = "none"
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"

    # 개인정보
    CHAT_LOG_RETENTION_DAYS: int = 30

    # Idempotency
    IDEMPOTENCY_TTL_SECONDS: int = 60

    # Admin 초기값
    ADMIN_DEFAULT_EMAIL: str = "admin@smartbot.kr"
    ADMIN_DEFAULT_PASSWORD: str = "changeme123!"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# 설정 우선순위:
# 1 (최고) TenantConfig DB 값 → 해당 테넌트에만 적용
# 2 환경변수 (.env) → 서버 전체 기본값
# 3 (최저) 코드 하드코딩 → 폴백


async def get_tenant_config(tenant_id: str, db) -> dict:
    """TenantConfig에서 테넌트별 설정 로드. 없으면 전역 settings 사용."""
    from app.models.tenant import TenantConfig
    from sqlalchemy import select

    result = await db.execute(
        select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
    )
    configs = result.scalars().all()

    base = settings.model_dump()
    if not configs:
        return base

    overrides = {cfg.key: cfg.value for cfg in configs}
    return {**base, **overrides}
