"""
POST /engine/query — 채널 공통 엔진 API (웹 시뮬레이터)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.idempotency import IdempotencyCache
from app.services.routing import ResponseRouter
from app.services.complaint_logger import log_complaint
from app.services.moderation import ModerationService

router = APIRouter()


class EngineRequest(BaseModel):
    tenant: str
    utterance: str
    user_key: str
    channel: str = "web"
    request_id: Optional[str] = None


class EngineResponse(BaseModel):
    answer: str
    tier: str
    source: str
    citations: list[dict] = []
    request_id: Optional[str] = None
    elapsed_ms: int = 0
    is_timeout: bool = False


@router.post("/engine/query", response_model=EngineResponse)
async def engine_query(
    body: EngineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = body.tenant
    request_id = body.request_id or str(uuid.uuid4())

    # Idempotency 캐시 확인
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client:
        cache = IdempotencyCache(redis_client)
        cached = await cache.get(tenant_id, request_id)
        if cached:
            return EngineResponse(**cached)

    # 악성 감지
    mod_service = ModerationService(db)
    mod_result = await mod_service.check(tenant_id, body.user_key)
    if not mod_result.allowed:
        return EngineResponse(
            answer=mod_result.message or "이용이 제한되었습니다. 담당 부서에 문의해 주세요.",
            tier="D",
            source="fallback",
            request_id=request_id,
        )

    # 라우터 실행
    providers = getattr(request.app.state, "providers", {})
    tenant_config = getattr(request.app.state, "tenant_configs", {}).get(
        tenant_id, settings.model_dump()
    )
    router_svc = ResponseRouter(tenant_config=tenant_config, providers=providers)
    result = await router_svc.route(
        tenant_id=tenant_id,
        utterance=body.utterance,
        user_key=body.user_key,
        request_id=request_id,
        db=db,
    )

    # 경고 메시지 추가 (Level 1)
    if mod_result.message and mod_result.level == 1:
        result.answer = f"{mod_result.message}\n\n{result.answer}"

    resp_dict = result.to_dict()

    # Idempotency 캐시 저장
    if redis_client:
        await cache.set(tenant_id, request_id, resp_dict)

    # 민원 이력 저장 (fire-and-forget: 실패해도 응답 영향 없음)
    try:
        await log_complaint(
            db=db,
            tenant_id=tenant_id,
            raw_utterance=body.utterance,
            raw_user_id=body.user_key,
            result=result,
            channel=body.channel,
        )
    except Exception:
        pass

    return EngineResponse(
        answer=result.answer,
        tier=result.tier,
        source=result.source,
        citations=resp_dict.get("citations", []),
        request_id=request_id,
        elapsed_ms=result.elapsed_ms,
        is_timeout=result.is_timeout,
    )
