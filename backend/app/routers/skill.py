"""
POST /skill/{tenant_slug} — 카카오 스킬 API
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.masking import mask_text, hash_user_key
from app.services.idempotency import IdempotencyCache
from app.services.routing import ResponseRouter
from app.services.complaint_logger import log_complaint
from app.services.moderation import ModerationService

router = APIRouter()


class KakaoUserRequest(BaseModel):
    utterance: str
    user: Optional[dict] = None


class KakaoSkillRequest(BaseModel):
    userRequest: KakaoUserRequest
    action: Optional[dict] = None


def build_kakao_response(answer: str, doc_name: Optional[str] = None) -> dict:
    quick_replies = []
    if doc_name:
        quick_replies.append({
            "label": "출처 보기",
            "action": "message",
            "messageText": f"출처: {doc_name}",
        })
    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": answer}}],
        },
    }
    if quick_replies:
        response["template"]["quickReplies"] = quick_replies
    return response


@router.post("/skill/{tenant_slug}")
async def kakao_skill(
    tenant_slug: str,
    body: KakaoSkillRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    utterance = body.userRequest.utterance
    raw_user_id = (body.userRequest.user or {}).get("id", "anonymous")

    masked_utterance = mask_text(utterance)
    user_key = hash_user_key(raw_user_id)

    action_params = (body.action or {}).get("params", {})
    request_id = action_params.get("request_id") or str(uuid.uuid4())

    # Idempotency 캐시 확인
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client:
        cache = IdempotencyCache(redis_client)
        cached = await cache.get(tenant_slug, request_id)
        if cached:
            return build_kakao_response(cached.get("answer", ""), cached.get("doc_name"))

    # 악성 감지
    mod_service = ModerationService(db)
    mod_result = await mod_service.check(tenant_slug, user_key)
    if not mod_result.allowed:
        answer = mod_result.message or "이용이 제한되었습니다. 담당 부서에 문의해 주세요."
        return build_kakao_response(answer)

    # 라우터 실행
    providers = getattr(request.app.state, "providers", {})
    tenant_config = getattr(request.app.state, "tenant_configs", {}).get(
        tenant_slug, settings.model_dump()
    )
    router_svc = ResponseRouter(tenant_config=tenant_config, providers=providers)
    result = await router_svc.route(
        tenant_id=tenant_slug,
        utterance=utterance,
        user_key=user_key,
        request_id=request_id,
        db=db,
    )

    if mod_result.message and mod_result.level == 1:
        result.answer = f"{mod_result.message}\n\n{result.answer}"

    # Idempotency 캐시 저장
    if redis_client:
        await cache.set(tenant_slug, request_id, result.to_dict())

    # 민원 이력 저장
    try:
        await log_complaint(
            db=db,
            tenant_id=tenant_slug,
            raw_utterance=utterance,
            raw_user_id=raw_user_id,
            result=result,
            channel="kakao",
        )
    except Exception:
        pass

    return build_kakao_response(result.answer, result.doc_name)
