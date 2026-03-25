"""Initial schema: 10 tables

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "system_admins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("hashed_pw", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "tenant_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("hashed_pw", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="viewer"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "email", name="uq_admin_users_tenant_email"),
    )

    op.create_table(
        "faqs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("keywords", sa.JSON()),
        sa.Column("hit_count", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_url", sa.Text()),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("effective_date", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("is_active", sa.Boolean(), default=False),
        sa.Column("approved_by", sa.String(36)),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("documents.id")),
        sa.Column("chunk_count", sa.Integer(), default=0),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "crawler_urls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_type", sa.String(50)),
        sa.Column("interval_hours", sa.Integer(), default=24),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_crawled", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "complaint_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_key", sa.String(64)),
        sa.Column("utterance_masked", sa.String(1000)),
        sa.Column("utterance_vec_id", sa.String(36)),
        sa.Column("channel", sa.String(20), default="kakao"),
        sa.Column("request_id", sa.String(36)),
        sa.Column("response_tier", sa.String(1)),
        sa.Column("response_source", sa.String(20)),
        sa.Column("faq_id", sa.String(36), sa.ForeignKey("faqs.id")),
        sa.Column("doc_id", sa.String(36), sa.ForeignKey("documents.id")),
        sa.Column("response_ms", sa.Integer()),
        sa.Column("is_timeout", sa.Boolean(), default=False),
        sa.Column("is_promoted", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "user_restrictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_key", sa.String(64), nullable=False),
        sa.Column("level", sa.Integer(), default=0),
        sa.Column("reason", sa.String(500)),
        sa.Column("applied_by", sa.String(36)),
        sa.Column("auto_applied", sa.Boolean(), default=True),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_key", name="uq_user_restrictions_tenant_user"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50)),
        sa.Column("target_id", sa.String(36)),
        sa.Column("diff", sa.JSON()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_restrictions")
    op.drop_table("complaint_logs")
    op.drop_table("crawler_urls")
    op.drop_table("documents")
    op.drop_table("faqs")
    op.drop_table("admin_users")
    op.drop_table("tenant_configs")
    op.drop_table("system_admins")
    op.drop_table("tenants")
