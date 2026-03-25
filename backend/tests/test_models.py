import pytest
from sqlalchemy import inspect, String, VARCHAR

from app.models.tenant import Tenant, TenantConfig
from app.models.admin import SystemAdmin, AdminUser, AdminRole
from app.models.knowledge import FAQ, Document, CrawlerURL
from app.models.complaint import ComplaintLog
from app.models.moderation import UserRestriction, RestrictionLevel
from app.models.audit import AuditLog

TENANT_REQUIRED_MODELS = [
    TenantConfig, FAQ, Document, CrawlerURL, ComplaintLog, UserRestriction, AuditLog, AdminUser
]


def get_column(model, col_name):
    """모델에서 컬럼 객체 반환."""
    for col in model.__table__.columns:
        if col.name == col_name:
            return col
    return None


def test_all_tenant_models_have_tenant_id():
    """8개 모델 모두 tenant_id 컬럼 포함 확인."""
    for model in TENANT_REQUIRED_MODELS:
        col = get_column(model, "tenant_id")
        assert col is not None, f"{model.__tablename__} must have tenant_id column"


def test_system_admin_has_no_tenant_id():
    """SystemAdmin 테이블에 tenant_id 없음 확인."""
    col = get_column(SystemAdmin, "tenant_id")
    assert col is None, "SystemAdmin must NOT have tenant_id column"


def test_all_pk_are_uuid_string():
    """모든 모델 PK 컬럼 타입이 VARCHAR(36) 또는 String."""
    all_models = [Tenant, TenantConfig, SystemAdmin, AdminUser, FAQ, Document,
                  CrawlerURL, ComplaintLog, UserRestriction, AuditLog]
    for model in all_models:
        pk_cols = [c for c in model.__table__.columns if c.primary_key]
        assert len(pk_cols) > 0, f"{model.__tablename__} has no PK"
        for col in pk_cols:
            col_type = str(col.type)
            assert "VARCHAR" in col_type or "CHAR" in col_type or isinstance(col.type, String), \
                f"{model.__tablename__}.{col.name} PK must be String/VARCHAR, got {col_type}"


def test_admin_user_email_not_globally_unique():
    """AdminUser.email 컬럼의 unique=False 확인."""
    col = get_column(AdminUser, "email")
    assert col is not None
    assert not col.unique, "AdminUser.email must NOT be globally unique (use tenant-scoped constraint)"


def test_system_admin_email_globally_unique():
    """SystemAdmin.email 컬럼의 unique=True 확인."""
    col = get_column(SystemAdmin, "email")
    assert col is not None
    assert col.unique, "SystemAdmin.email must be globally unique"


def test_document_is_active_default_false():
    """Document.is_active 기본값이 False 확인."""
    col = get_column(Document, "is_active")
    assert col is not None
    assert col.default.arg is False, "Document.is_active default must be False"


def test_complaint_log_has_request_id():
    """ComplaintLog에 request_id 컬럼 존재 확인."""
    col = get_column(ComplaintLog, "request_id")
    assert col is not None, "ComplaintLog must have request_id column"


def test_audit_log_has_required_columns():
    """AuditLog에 actor_id, actor_type, action, tenant_id 확인."""
    required = ["actor_id", "actor_type", "action", "tenant_id"]
    for col_name in required:
        col = get_column(AuditLog, col_name)
        assert col is not None, f"AuditLog must have {col_name} column"


def test_user_restriction_level_range():
    """RestrictionLevel.NORMAL==0, BLOCKED==5."""
    assert RestrictionLevel.NORMAL == 0
    assert RestrictionLevel.BLOCKED == 5


def test_admin_role_values():
    """AdminRole 값 집합 == {'admin','editor','viewer','readonly_api'}."""
    expected = {"admin", "editor", "viewer", "readonly_api"}
    actual = {role.value for role in AdminRole}
    assert actual == expected
