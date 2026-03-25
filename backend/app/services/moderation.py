"""
악성·반복 민원 제한 서비스.

Level  상태         자동 조치              해제
0      정상         없음                   자동
1      주의         경고 메시지            자동
2      경고         30초 응답 지연         자동 24h
3      제한         10회/일 제한           자동 72h
4      임시 차단    24시간 차단            편집장 수동 확인 필요
5      영구 제한    차단 유지              편집장 수동 해제만

원칙: 자동 영구 차단 없음. Level 4+ 는 편집장 수동 확인.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation import UserRestriction, RestrictionLevel

# 레벨별 자동 만료 시간
LEVEL_EXPIRY = {
    RestrictionLevel.WARNING: timedelta(hours=24),
    RestrictionLevel.LIMITED: timedelta(hours=72),
    RestrictionLevel.SUSPENDED: timedelta(hours=24),  # 편집장 확인 전 임시
}

# 레벨 3 일별 제한 횟수
DAILY_LIMIT = 10

# 레벨 1 경고 메시지
WARNING_MESSAGE = "⚠️ 동일 문의가 반복되고 있습니다. 잠시 후 다시 시도해 주세요."


class ModerationResult:
    def __init__(
        self,
        allowed: bool,
        level: int = 0,
        message: Optional[str] = None,
        delay_seconds: int = 0,
    ):
        self.allowed = allowed
        self.level = level
        self.message = message  # 경고 메시지 (Level 1)
        self.delay_seconds = delay_seconds  # 응답 지연 (Level 2)


class ModerationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check(self, tenant_id: str, user_key: str) -> ModerationResult:
        """
        user_key의 제한 레벨 확인.
        만료된 제한은 자동 해제.
        """
        restriction = await self._get_restriction(tenant_id, user_key)

        if restriction is None:
            return ModerationResult(allowed=True, level=0)

        # 만료 확인
        if restriction.expires_at and restriction.expires_at < datetime.now(timezone.utc):
            if restriction.level < RestrictionLevel.SUSPENDED:
                await self._reset(restriction)
                return ModerationResult(allowed=True, level=0)

        level = restriction.level

        if level == RestrictionLevel.BLOCKED:
            return ModerationResult(allowed=False, level=level)

        if level == RestrictionLevel.SUSPENDED:
            # Level 4: 편집장 확인 전 차단
            return ModerationResult(allowed=False, level=level)

        if level == RestrictionLevel.LIMITED:
            # Level 3: 일별 10회 제한 (Redis 카운터 없이 단순 차단)
            return ModerationResult(
                allowed=False,
                level=level,
                message="일일 문의 한도에 도달했습니다. 내일 다시 시도해 주세요.",
            )

        if level == RestrictionLevel.WARNING:
            # Level 2: 30초 지연
            return ModerationResult(
                allowed=True,
                level=level,
                delay_seconds=30,
                message="요청이 지연되고 있습니다.",
            )

        if level == RestrictionLevel.NORMAL + 1:  # Level 1 (WARNING 사용하기 전 단계는 없으므로 1 = 주의)
            return ModerationResult(
                allowed=True,
                level=level,
                message=WARNING_MESSAGE,
            )

        return ModerationResult(allowed=True, level=level)

    async def escalate(
        self,
        tenant_id: str,
        user_key: str,
        reason: str = "자동 감지",
    ) -> int:
        """
        레벨 1단계 상승. Level 4+ 는 편집장 수동 확인.
        반환: 새 레벨.
        """
        restriction = await self._get_restriction(tenant_id, user_key)

        if restriction is None:
            restriction = UserRestriction(
                tenant_id=tenant_id,
                user_key=user_key,
                level=RestrictionLevel.NORMAL,
                auto_applied=True,
            )
            self.db.add(restriction)

        current = restriction.level
        if current >= RestrictionLevel.SUSPENDED:
            # Level 4+ 는 자동 상승 금지
            return current

        new_level = min(current + 1, RestrictionLevel.SUSPENDED)
        restriction.level = new_level
        restriction.reason = reason
        restriction.auto_applied = True

        # 만료 시간 설정
        expiry_delta = LEVEL_EXPIRY.get(new_level)
        if expiry_delta:
            restriction.expires_at = datetime.now(timezone.utc) + expiry_delta
        else:
            restriction.expires_at = None

        await self.db.commit()
        return new_level

    async def release(
        self,
        tenant_id: str,
        user_key: str,
        applied_by: str,
    ) -> None:
        """수동 해제 (편집장 이상)."""
        restriction = await self._get_restriction(tenant_id, user_key)
        if restriction:
            await self._reset(restriction, applied_by=applied_by)

    async def _get_restriction(
        self, tenant_id: str, user_key: str
    ) -> Optional[UserRestriction]:
        result = await self.db.execute(
            select(UserRestriction).where(
                UserRestriction.tenant_id == tenant_id,
                UserRestriction.user_key == user_key,
            )
        )
        return result.scalar_one_or_none()

    async def _reset(self, restriction: UserRestriction, applied_by: Optional[str] = None) -> None:
        restriction.level = RestrictionLevel.NORMAL
        restriction.expires_at = None
        restriction.auto_applied = applied_by is None
        if applied_by:
            restriction.applied_by = applied_by
        await self.db.commit()
