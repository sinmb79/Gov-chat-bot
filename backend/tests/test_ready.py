import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_ready_ok_when_all_services_up(client):
    """DB/Redis mock 정상 → GET /ready → 200, ready=True."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    with patch("app.routers.health.aioredis.from_url", return_value=mock_redis):
        response = await client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["checks"]["db"] == "ok"


@pytest.mark.asyncio
async def test_ready_503_when_db_down(client):
    """DB mock 오류 → GET /ready → 503, ready=False."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    # DB 연결 실패 시뮬레이션
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    with patch("app.routers.health.aioredis.from_url", return_value=mock_redis), \
         patch("app.routers.health.AsyncSessionLocal", return_value=mock_session):
        response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["ready"] is False
