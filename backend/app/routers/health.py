import redis.asyncio as aioredis
from fastapi import APIRouter, Response
from sqlalchemy import text

import app.providers as providers_module
from app.core.config import settings
from app.core.database import AsyncSessionLocal

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "phase": "0B", "version": "0.2.0"}


@router.get("/ready")
async def ready(response: Response):
    checks = {}
    all_ok = True

    # DB 확인
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        all_ok = False

    # Redis 확인
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        all_ok = False

    # Embedding 워밍업 상태
    checks["embedding"] = "warmed_up" if providers_module._embedding_warmed_up else "not_warmed_up"

    if all_ok:
        return {"ready": True, "checks": checks}
    else:
        response.status_code = 503
        return {"ready": False, "checks": checks}
