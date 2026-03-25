from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Phase 0B에서 settings로 교체 예정 — 현재는 하드코딩 허용
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def startup_hook():
    """Phase 0B startup 훅 — DB 초기화 + 추가 작업 예정."""
    await init_db()
