import json
from typing import Optional

from app.services.routing import RoutingResult

METRIC_KEYS = [
    "total_count",
    "faq_hit_count",
    "rag_hit_count",
    "llm_hit_count",
    "fallback_count",
    "timeout_count",
    "response_ms_sum",
    "blocked_attempts",
]

P95_SORTED_SET = "response_ms_p95_buf"
P95_MAX_SIZE = 10000

_SOURCE_TO_KEY = {
    "faq": "faq_hit_count",
    "rag": "rag_hit_count",
    "llm": "llm_hit_count",
    "fallback": "fallback_count",
}


class MetricsCollector:
    def __init__(self, redis_client):
        self.redis = redis_client

    def _prefix(self, tenant_id: str) -> str:
        return f"tenant:{tenant_id}:metrics"

    def _p95_key(self, tenant_id: str) -> str:
        return f"tenant:{tenant_id}:{P95_SORTED_SET}"

    async def record(self, tenant_id: str, result: RoutingResult) -> None:
        prefix = self._prefix(tenant_id)
        p95_key = self._p95_key(tenant_id)

        pipe = self.redis.pipeline()
        pipe.hincrby(prefix, "total_count", 1)

        source_key = _SOURCE_TO_KEY.get(result.source)
        if source_key:
            pipe.hincrby(prefix, source_key, 1)

        if result.is_timeout:
            pipe.hincrby(prefix, "timeout_count", 1)

        pipe.hincrby(prefix, "response_ms_sum", result.elapsed_ms)

        # p95 sorted set — score=elapsed_ms, member=unique id
        import time
        member = f"{time.time_ns()}"
        pipe.zadd(p95_key, {member: result.elapsed_ms})
        pipe.zremrangebyrank(p95_key, 0, -(P95_MAX_SIZE + 1))

        await pipe.execute()

    async def get_overview(self, tenant_id: str) -> dict:
        prefix = self._prefix(tenant_id)
        p95_key = self._p95_key(tenant_id)

        raw = await self.redis.hgetall(prefix)
        counts = {k: int(v) for k, v in raw.items()} if raw else {}

        total = counts.get("total_count", 0)
        avg_ms = counts.get("response_ms_sum", 0) // max(total, 1)

        # p95 계산
        p95_ms = 0
        buf_size = await self.redis.zcard(p95_key)
        if buf_size > 0:
            p95_idx = max(0, int(buf_size * 0.95) - 1)
            p95_items = await self.redis.zrange(p95_key, p95_idx, p95_idx, withscores=True)
            if p95_items:
                p95_ms = int(p95_items[0][1])

        rates = {}
        if total > 0:
            rates["faq_hit_rate"] = round(counts.get("faq_hit_count", 0) / total * 100, 2)
            rates["rag_hit_rate"] = round(counts.get("rag_hit_count", 0) / total * 100, 2)
            rates["fallback_rate"] = round(counts.get("fallback_count", 0) / total * 100, 2)
            rates["timeout_rate"] = round(counts.get("timeout_count", 0) / total * 100, 2)
        else:
            rates = {"faq_hit_rate": 0.0, "rag_hit_rate": 0.0, "fallback_rate": 0.0, "timeout_rate": 0.0}

        return {
            "counts": counts,
            "rates": rates,
            "avg_ms": avg_ms,
            "p95_ms": p95_ms,
        }
