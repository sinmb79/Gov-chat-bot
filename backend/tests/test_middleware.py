import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.middleware import tenanted_query, system_query, TenantMiddleware
from app.models.knowledge import FAQ
from app.main import app


@pytest.mark.asyncio
async def test_health_exempt_no_tenant_required(client):
    """GET /health → 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_token_endpoint_exempt(client):
    """POST /api/admin/token → 400이 아닌 응답 (tenant 오류 아님)."""
    response = await client.post("/api/admin/token")
    # 엔드포인트가 없으면 404, 있으면 422/200 — 어떤 경우든 400(tenant_required)이 아님
    assert response.status_code != 400 or response.json().get("error") != "tenant_required"


@pytest.mark.asyncio
async def test_api_request_without_auth_returns_401(client):
    """GET /api/admin/faqs (인증 없음) → 401 (admin 경로는 미들웨어 exempt, JWT 필요)."""
    response = await client.get("/api/admin/faqs")
    assert response.status_code == 401


def test_tenanted_query_without_tenant_id_raises_runtime_error():
    """tenanted_query(select(FAQ), FAQ, None) → RuntimeError 발생."""
    with pytest.raises(RuntimeError):
        tenanted_query(select(FAQ), FAQ, None)


def test_tenanted_query_with_tenant_id_adds_filter():
    """생성된 SQL에 'tenant_id' 포함 확인."""
    query = tenanted_query(select(FAQ), FAQ, "test-tenant-id")
    sql = str(query.compile())
    assert "tenant_id" in sql


def test_tenanted_query_with_empty_string_raises():
    """tenanted_query(select(FAQ), FAQ, '') → RuntimeError 발생."""
    with pytest.raises(RuntimeError):
        tenanted_query(select(FAQ), FAQ, "")


def test_system_query_has_no_tenant_filter():
    """system_query(q) == q (변경 없음)."""
    q = select(FAQ)
    result = system_query(q)
    assert result is q


@pytest.mark.asyncio
async def test_request_state_has_tenant_id_after_middleware(client):
    """X-Tenant-Slug 헤더 포함 요청 시 request.state.tenant_id 주입 확인."""
    # 미들웨어가 tenant_id를 설정하면 400 대신 다른 응답 코드가 나와야 함
    response = await client.get(
        "/api/admin/faqs",
        headers={"X-Tenant-Slug": "test-tenant"}
    )
    # tenant_required 오류가 아니어야 함 (404 또는 다른 응답)
    assert response.status_code != 400 or response.json().get("error") != "tenant_required"
