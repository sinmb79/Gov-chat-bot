"""
관리자 인증 API 테스트.
POST /api/admin/auth/login
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.admin import AdminUser, AdminRole
from app.core.security import hash_password


def make_user(tenant_id: str = "t1", email: str = "admin@test.com") -> AdminUser:
    user = AdminUser()
    user.id = str(uuid4())
    user.tenant_id = tenant_id
    user.email = email
    user.hashed_pw = hash_password("secret123")
    user.role = AdminRole.admin
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_login_success(client):
    """올바른 자격증명 → access_token + role 반환."""
    user = make_user()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=user)

    from app.core.database import get_db

    async def override_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    client.app.dependency_overrides[get_db] = override_db

    try:
        res = await client.post("/api/admin/auth/login", json={
            "tenant_id": user.tenant_id,
            "email": user.email,
            "password": "secret123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
    finally:
        client.app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """틀린 비밀번호 → 401."""
    user = make_user()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=user)

    from app.core.database import get_db

    async def override_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    client.app.dependency_overrides[get_db] = override_db

    try:
        res = await client.post("/api/admin/auth/login", json={
            "tenant_id": user.tenant_id,
            "email": user.email,
            "password": "wrong-password",
        })
        assert res.status_code == 401
    finally:
        client.app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_login_user_not_found(client):
    """존재하지 않는 사용자 → 401."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)

    from app.core.database import get_db

    async def override_db():
        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        yield db

    client.app.dependency_overrides[get_db] = override_db

    try:
        res = await client.post("/api/admin/auth/login", json={
            "tenant_id": "nonexistent",
            "email": "nobody@test.com",
            "password": "any",
        })
        assert res.status_code == 401
    finally:
        client.app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    """필수 필드 누락 → 422."""
    res = await client.post("/api/admin/auth/login", json={"email": "x@x.com"})
    assert res.status_code == 422
