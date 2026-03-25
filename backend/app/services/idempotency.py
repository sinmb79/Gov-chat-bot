import json
from typing import Optional


class IdempotencyCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 60  # 기본 TTL (Phase 0B에서 settings로 교체 예정)

    def _key(self, tenant_id: str, request_id: str) -> str:
        return f"idempotency:{tenant_id}:{request_id}"

    async def get(self, tenant_id: str, request_id: Optional[str]) -> Optional[dict]:
        if request_id is None:
            return None
        raw = await self.redis.get(self._key(tenant_id, request_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, tenant_id: str, request_id: Optional[str], result_dict: dict) -> None:
        if request_id is None:
            return
        await self.redis.setex(
            self._key(tenant_id, request_id),
            self.ttl,
            json.dumps(result_dict),
        )
