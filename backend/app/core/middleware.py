from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from sqlalchemy import select

EXEMPT_PATHS = {"/health", "/ready", "/engine/query", "/api/docs", "/openapi.json", "/redoc"}
EXEMPT_PREFIXES = ("/skill/", "/api/admin/")  # 채널 API + 관리자 API (JWT로 tenant 검증)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXEMPT_PATHS or any(path.startswith(p) for p in EXEMPT_PREFIXES):
            request.state.tenant_id = None
            return await call_next(request)

        tenant_id = await self._resolve_tenant(request)
        if not tenant_id:
            return JSONResponse({"error": "tenant_required"}, status_code=400)

        request.state.tenant_id = tenant_id
        return await call_next(request)

    async def _resolve_tenant(self, request: Request):
        # 현재는 X-Tenant-Slug 헤더만 처리 (Phase 0B에서 JWT 추가)
        slug = request.headers.get("X-Tenant-Slug")
        if slug:
            return slug
        return None


def tenanted_query(query, model, tenant_id):
    """
    주의: model 파라미터가 두 번째 인자다. (v2.0 오류 수정)
    tenant_id가 None 또는 빈 문자열이면 RuntimeError 발생.
    사용 예: tenanted_query(select(FAQ), FAQ, request.state.tenant_id)
    """
    if not tenant_id:
        raise RuntimeError(
            f"tenant_id is required for {model.__tablename__} queries. "
            "Check TenantMiddleware is applied."
        )
    return query.where(model.tenant_id == tenant_id)


def system_query(query):
    """SystemAdmin 전용 쿼리. tenant 필터 없음. 일반 서비스에서 호출 금지."""
    return query
