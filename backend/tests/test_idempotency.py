import pytest

from app.services.idempotency import IdempotencyCache


class FakeRedis:
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, ttl, value):
        self._store[key] = value


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    """get('tenant-1', 'req-1') == None (캐시 없음)."""
    cache = IdempotencyCache(FakeRedis())
    result = await cache.get("tenant-1", "req-1")
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_returns_same_data():
    """set 후 get → 동일 데이터."""
    cache = IdempotencyCache(FakeRedis())
    data = {"answer": "test", "tier": "A"}
    await cache.set("tenant-1", "req-1", data)
    result = await cache.get("tenant-1", "req-1")
    assert result == data


@pytest.mark.asyncio
async def test_different_tenant_same_request_id_no_collision():
    """tenant-A에 저장, tenant-B에서 같은 request_id get → None."""
    cache = IdempotencyCache(FakeRedis())
    await cache.set("tenant-A", "req-1", {"answer": "A"})
    result = await cache.get("tenant-B", "req-1")
    assert result is None


@pytest.mark.asyncio
async def test_no_request_id_returns_none():
    """get(tenant_id, None) == None."""
    cache = IdempotencyCache(FakeRedis())
    result = await cache.get("tenant-1", None)
    assert result is None
