from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import (
    hash_password,
    verify_password,
    create_admin_token,
    create_system_token,
    decode_token,
)
from app.core.config import settings


def test_hash_and_verify_password():
    """해싱 후 verify True, 다른 비밀번호는 False."""
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_admin_token_has_tenant_id():
    """decode 시 payload['tenant_id'] == 'tenant-id', type == 'admin_user'."""
    token = create_admin_token("user-1", "tenant-id", "admin")
    payload = decode_token(token)
    assert payload is not None
    assert payload["tenant_id"] == "tenant-id"
    assert payload["type"] == "admin_user"


def test_create_system_token_has_no_tenant_id():
    """decode 시 payload['tenant_id'] is None, type == 'system_admin'."""
    token = create_system_token("sys-admin-1")
    payload = decode_token(token)
    assert payload is not None
    assert payload["tenant_id"] is None
    assert payload["type"] == "system_admin"


def test_decode_invalid_token_returns_none():
    """decode_token('invalid.token') == None."""
    assert decode_token("invalid.token") is None


def test_decode_expired_token_returns_none():
    """만료 토큰 생성 후 decode == None."""
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    assert decode_token(expired_token) is None


def test_admin_and_system_token_different_type():
    """두 토큰의 type 필드 값 다름."""
    admin_token = create_admin_token("user-1", "tenant-1", "admin")
    system_token = create_system_token("sys-1")

    admin_payload = decode_token(admin_token)
    system_payload = decode_token(system_token)

    assert admin_payload["type"] != system_payload["type"]
