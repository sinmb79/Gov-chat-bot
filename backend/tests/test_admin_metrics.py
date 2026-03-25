"""
메트릭 조회 API 테스트.
GET /api/admin/metrics
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.admin import AdminUser, AdminRole
from app.core.security import create_admin_token, hash_password


def make_user(tenant_id: str = "t1") -> AdminUser:
    user = AdminUser()
    user.id = str(uuid4())
    user.tenant_id = tenant_id
    user.email = "admin@test.com"
    user.hashed_pw = hash_password("pw")
    user.role = AdminRole.admin
    user.is_active = True
    return user


def auth_headers(user: AdminUser) -> dict:
    token = create_admin_token(user.id, user.tenant_id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_metrics_no_auth_returns_401(client):
    """인증 없이 접근 → 401."""
    res = await client.get("/api/admin/metrics")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_metrics_db_fallback(client):
    """Redis 없을 때 DB 집계로 메트릭 반환."""
    user = make_user()

    call_count = 0

    async def fake_execute(query):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            # get_current_admin: AdminUser 조회
            mock.scalar_one_or_none = MagicMock(return_value=user)
            return mock
        sql = str(query)
        if "response_tier" in sql or "group_by" in sql.lower():
            mock.all = MagicMock(return_value=[("A", 5), ("B", 3), ("D", 2)])
        elif "is_timeout" in sql:
            mock.scalar = MagicMock(return_value=1)
        else:
            mock.scalar = MagicMock(return_value=10)
        return mock

    from app.core.database import get_db

    async def override_db():
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=fake_execute)
        yield db

    client.app.dependency_overrides[get_db] = override_db
    client.app.state.redis = None

    try:
        res = await client.get("/api/admin/metrics", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert "total_count" in data
        assert "tier_counts" in data
        assert "timeout_count" in data
        assert set(data["tier_counts"].keys()) == {"A", "B", "C", "D"}
    finally:
        client.app.dependency_overrides.pop(get_db, None)
