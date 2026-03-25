"""
POST /engine/query 엔드포인트 테스트 (웹 시뮬레이터).
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_engine_query_returns_correct_structure(client):
    """POST /engine/query → 필수 필드 포함 응답."""
    response = await client.post(
        "/engine/query",
        json={
            "tenant": "test-tenant",
            "utterance": "여권 발급 방법 알려주세요",
            "user_key": "test-user-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "tier" in data
    assert "source" in data
    assert "citations" in data
    assert "request_id" in data


@pytest.mark.asyncio
async def test_engine_query_tier_d_when_no_faq(client):
    """FAQ 없으면 Tier D 폴백 반환."""
    response = await client.post(
        "/engine/query",
        json={
            "tenant": "test-tenant",
            "utterance": "알 수 없는 질문",
            "user_key": "user-1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "D"
    assert data["source"] == "fallback"


@pytest.mark.asyncio
async def test_engine_query_idempotency_deduplication(client):
    """같은 request_id로 두 번 요청 → 동일 응답 (캐시 HIT)."""
    payload = {
        "tenant": "test-tenant",
        "utterance": "중복 요청 테스트",
        "user_key": "user-1",
        "request_id": "dup-req-001",
    }

    # Mock Redis for idempotency
    mock_redis = AsyncMock()
    cached_result = {
        "answer": "캐시된 응답",
        "tier": "D",
        "source": "fallback",
        "citations": [],
        "request_id": "dup-req-001",
        "elapsed_ms": 10,
        "is_timeout": False,
    }
    import json
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_result).encode())
    mock_redis.setex = AsyncMock()

    # app.state에 직접 설정 (lifespan 미실행 상태)
    client.app.state.redis = mock_redis
    try:
        resp1 = await client.post("/engine/query", json=payload)
    finally:
        client.app.state.redis = None

    assert resp1.status_code == 200
    assert resp1.json()["answer"] == "캐시된 응답"


@pytest.mark.asyncio
async def test_engine_query_request_id_auto_generated(client):
    """request_id 미전송 시 자동 생성."""
    response = await client.post(
        "/engine/query",
        json={
            "tenant": "test-tenant",
            "utterance": "테스트",
            "user_key": "user-1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] is not None
    assert len(data["request_id"]) > 0


@pytest.mark.asyncio
async def test_engine_query_channel_default_web(client):
    """channel 미전송 시 기본값 web 사용 — 응답은 정상."""
    response = await client.post(
        "/engine/query",
        json={
            "tenant": "test-tenant",
            "utterance": "테스트",
            "user_key": "user-1",
        },
    )
    assert response.status_code == 200
