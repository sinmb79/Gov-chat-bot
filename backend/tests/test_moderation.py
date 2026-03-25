"""
악성·반복 민원 제한 서비스 테스트.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.moderation import ModerationService, ModerationResult
from app.models.moderation import UserRestriction, RestrictionLevel


def make_db(restriction=None):
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    scalar = MagicMock()
    scalar.scalar_one_or_none = MagicMock(return_value=restriction)
    db.execute.return_value = scalar
    return db


@pytest.mark.asyncio
async def test_check_normal_user_is_allowed():
    """제한 없는 사용자 → 허용."""
    db = make_db(restriction=None)
    service = ModerationService(db)
    result = await service.check("t1", "user-1")
    assert result.allowed is True
    assert result.level == 0


@pytest.mark.asyncio
async def test_check_blocked_user_is_denied():
    """Level 5 (BLOCKED) → 차단."""
    r = MagicMock()
    r.level = RestrictionLevel.BLOCKED
    r.expires_at = None
    db = make_db(restriction=r)

    service = ModerationService(db)
    result = await service.check("t1", "user-block")
    assert result.allowed is False
    assert result.level == RestrictionLevel.BLOCKED


@pytest.mark.asyncio
async def test_check_suspended_user_is_denied():
    """Level 4 (SUSPENDED) → 편집장 확인 전 차단."""
    r = MagicMock()
    r.level = RestrictionLevel.SUSPENDED
    r.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db = make_db(restriction=r)

    service = ModerationService(db)
    result = await service.check("t1", "user-sus")
    assert result.allowed is False


@pytest.mark.asyncio
async def test_check_warning_user_has_delay():
    """Level 2 (WARNING) → 허용 + 30초 지연."""
    r = MagicMock()
    r.level = RestrictionLevel.WARNING
    r.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db = make_db(restriction=r)

    service = ModerationService(db)
    result = await service.check("t1", "user-warn")
    assert result.allowed is True
    assert result.delay_seconds == 30


@pytest.mark.asyncio
async def test_escalate_increases_level():
    """레벨 상승: NORMAL → 다음 레벨."""
    r = MagicMock(spec=UserRestriction)
    r.level = RestrictionLevel.NORMAL
    r.expires_at = None
    r.auto_applied = True

    db = make_db(restriction=r)

    service = ModerationService(db)
    new_level = await service.escalate("t1", "user-1", "반복 민원")

    assert new_level == RestrictionLevel.NORMAL + 1
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_escalate_stops_at_suspended():
    """Level 4 이상 자동 상승 금지."""
    r = MagicMock(spec=UserRestriction)
    r.level = RestrictionLevel.SUSPENDED
    r.expires_at = None

    db = make_db(restriction=r)

    service = ModerationService(db)
    new_level = await service.escalate("t1", "user-1")

    # Level 4에서 멈춤
    assert new_level == RestrictionLevel.SUSPENDED


@pytest.mark.asyncio
async def test_release_resets_level():
    """수동 해제 → level 0."""
    r = MagicMock(spec=UserRestriction)
    r.level = RestrictionLevel.SUSPENDED
    r.expires_at = None
    r.auto_applied = True
    r.applied_by = None

    db = make_db(restriction=r)

    service = ModerationService(db)
    await service.release("t1", "user-1", applied_by="editor-1")

    assert r.level == RestrictionLevel.NORMAL
    assert r.applied_by == "editor-1"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_expired_restriction_resets():
    """만료된 제한 → 자동 해제."""
    r = MagicMock(spec=UserRestriction)
    r.level = RestrictionLevel.WARNING  # Level 2
    r.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # 만료
    r.auto_applied = True
    r.applied_by = None

    db = make_db(restriction=r)

    service = ModerationService(db)
    result = await service.check("t1", "user-expired")

    assert result.allowed is True
    assert result.level == 0
