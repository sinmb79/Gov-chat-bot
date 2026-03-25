import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metrics import MetricsCollector
from app.services.routing import RoutingResult


def make_result(source="faq", elapsed_ms=100, is_timeout=False):
    return RoutingResult(
        answer="test",
        tier="A",
        source=source,
        elapsed_ms=elapsed_ms,
        is_timeout=is_timeout,
    )


class FakePipeline:
    def __init__(self):
        self._data = {}
        self._sets = {}
        self._calls = []

    def hincrby(self, key, field, amount):
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = self._data[key].get(field, 0) + amount
        return self

    def zadd(self, key, mapping):
        if key not in self._sets:
            self._sets[key] = {}
        self._sets[key].update(mapping)
        return self

    def zremrangebyrank(self, key, start, stop):
        return self

    async def execute(self):
        return []


class FakeRedis:
    def __init__(self):
        self._data = {}
        self._sets = {}
        self._pipeline = FakePipeline()

    def pipeline(self):
        return self._pipeline

    async def hgetall(self, key):
        return {k: str(v) for k, v in self._pipeline._data.get(key, {}).items()}

    async def zcard(self, key):
        return len(self._pipeline._sets.get(key, {}))

    async def zrange(self, key, start, stop, withscores=False):
        items = sorted(self._pipeline._sets.get(key, {}).items(), key=lambda x: x[1])
        slice_ = items[start:stop + 1 if stop >= 0 else None]
        if withscores:
            return [(k.encode(), v) for k, v in slice_]
        return [k.encode() for k, _ in slice_]


@pytest.mark.asyncio
async def test_record_increments_total_count():
    """record 후 total_count == 1."""
    redis = FakeRedis()
    collector = MetricsCollector(redis)
    result = make_result(source="faq")
    await collector.record("tenant-1", result)
    assert redis._pipeline._data.get("tenant:tenant-1:metrics", {}).get("total_count", 0) == 1


@pytest.mark.asyncio
async def test_record_faq_increments_faq_hit_count():
    """source='faq'인 result record 후 faq_hit_count == 1."""
    redis = FakeRedis()
    collector = MetricsCollector(redis)
    await collector.record("tenant-1", make_result(source="faq"))
    counts = redis._pipeline._data.get("tenant:tenant-1:metrics", {})
    assert counts.get("faq_hit_count", 0) == 1


@pytest.mark.asyncio
async def test_record_timeout_increments_timeout_count():
    """is_timeout=True인 result record 후 timeout_count == 1."""
    redis = FakeRedis()
    collector = MetricsCollector(redis)
    await collector.record("tenant-1", make_result(is_timeout=True))
    counts = redis._pipeline._data.get("tenant:tenant-1:metrics", {})
    assert counts.get("timeout_count", 0) == 1


@pytest.mark.asyncio
async def test_get_overview_returns_rates():
    """total=10, faq=4 → faq_hit_rate == 40.0."""
    redis = FakeRedis()
    collector = MetricsCollector(redis)

    # 수동으로 pipeline 데이터 설정
    redis._pipeline._data["tenant:tenant-1:metrics"] = {
        "total_count": 10,
        "faq_hit_count": 4,
        "rag_hit_count": 2,
        "fallback_count": 3,
        "timeout_count": 1,
        "response_ms_sum": 1000,
    }

    overview = await collector.get_overview("tenant-1")
    assert overview["rates"]["faq_hit_rate"] == 40.0
