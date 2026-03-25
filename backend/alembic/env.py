import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# 모델 임포트 (테이블 메타데이터 등록)
from app.core.database import Base
import app.models.tenant
import app.models.admin
import app.models.knowledge
import app.models.complaint
import app.models.moderation
import app.models.audit

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """settings의 DATABASE_URL에서 asyncpg → psycopg2 변환."""
    from app.core.config import settings
    url = settings.DATABASE_URL
    # asyncpg → psycopg2 (Alembic은 동기 연결 사용)
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
