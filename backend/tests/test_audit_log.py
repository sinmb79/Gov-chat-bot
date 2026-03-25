"""
감사 로그 단위 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call

from app.services.audit import log_action
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_log_action_creates_audit_entry():
    """log_action 호출 시 AuditLog 추가 및 커밋."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    entry = await log_action(
        db=db,
        tenant_id="tenant-1",
        actor_id="user-1",
        actor_type="admin_user",
        action="doc.upload",
        target_type="document",
        target_id="doc-1",
        diff={"filename": "guide.txt"},
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert entry.action == "doc.upload"
    assert entry.tenant_id == "tenant-1"
    assert entry.actor_id == "user-1"


@pytest.mark.asyncio
async def test_log_action_doc_approve():
    """doc.approve 액션 기록."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    entry = await log_action(
        db=db,
        tenant_id="t1",
        actor_id="editor-1",
        actor_type="admin_user",
        action="doc.approve",
        target_type="document",
        target_id="doc-2",
    )

    assert entry.action == "doc.approve"
    assert entry.target_id == "doc-2"


@pytest.mark.asyncio
async def test_log_action_includes_diff():
    """diff 필드가 저장됨."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    diff = {"before": "pending", "after": "processed"}
    entry = await log_action(
        db=db,
        tenant_id="t1",
        actor_id="user-1",
        actor_type="admin_user",
        action="config.update",
        diff=diff,
    )

    assert entry.diff == diff


@pytest.mark.asyncio
async def test_log_action_without_target():
    """target_type/target_id 없어도 정상 기록."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    entry = await log_action(
        db=db,
        tenant_id="t1",
        actor_id="user-1",
        actor_type="system_admin",
        action="config.update",
    )

    assert entry.target_type is None
    assert entry.target_id is None


@pytest.mark.asyncio
async def test_log_crawler_approve():
    """crawler.approve 감사 로그."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    entry = await log_action(
        db=db,
        tenant_id="t1",
        actor_id="editor-1",
        actor_type="admin_user",
        action="crawler.approve",
        target_type="crawler_url",
        target_id="url-1",
        diff={"url": "https://www.dongducheon.go.kr"},
    )

    assert entry.action == "crawler.approve"
    assert entry.diff["url"] == "https://www.dongducheon.go.kr"
