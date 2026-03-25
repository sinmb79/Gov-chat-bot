from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import startup_hook
from app.core.middleware import TenantMiddleware
from app.providers import get_embedding_provider, get_llm_provider, get_vectordb_provider
from app.routers import health
from app.routers import engine, skill
from app.routers import admin_docs, admin_crawler
from app.routers import admin_faq, admin_moderation, admin_complaints
from app.routers import admin_auth, admin_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_hook()

    # 전역 설정 로드
    cfg = settings.model_dump()

    # Provider 초기화
    embedding = get_embedding_provider(cfg)
    llm = get_llm_provider(cfg)
    vectordb = get_vectordb_provider(cfg)

    # 임베딩 워밍업 (시작 시 모델 로드)
    try:
        await embedding.warmup()
    except Exception:
        pass  # 실패해도 서버는 기동 — /ready에서 상태 노출

    app.state.providers = {
        "embedding": embedding,
        "llm": llm,
        "vectordb": vectordb,
    }
    app.state.tenant_configs = {}  # 캐시: {tenant_slug: config_dict}
    app.state.redis = None  # Phase 1: Redis 연결은 선택적

    # Redis 연결 시도
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        app.state.redis = r
    except Exception:
        pass  # Redis 없이도 동작 (Idempotency 비활성)

    yield

    # 종료 시 Redis 연결 해제
    if app.state.redis:
        await app.state.redis.aclose()


app = FastAPI(title="GovBot KR", version="1.0.0", lifespan=lifespan)

app.add_middleware(TenantMiddleware)
app.include_router(health.router)
app.include_router(engine.router)
app.include_router(skill.router)
app.include_router(admin_docs.router)
app.include_router(admin_crawler.router)
app.include_router(admin_auth.router)
app.include_router(admin_faq.router)
app.include_router(admin_moderation.router)
app.include_router(admin_complaints.router)
app.include_router(admin_metrics.router)
