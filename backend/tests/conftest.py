import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# 모든 모델을 명시적으로 임포트하여 Base.metadata에 등록 (FK 순서 보장)
from app.models import tenant as _m1       # noqa: F401
from app.models import admin as _m2        # noqa: F401
from app.models import knowledge as _m3   # noqa: F401
from app.models import complaint as _m4   # noqa: F401
from app.models import moderation as _m5  # noqa: F401
from app.models import audit as _m6       # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # app 참조를 client에 노출 (테스트에서 app.state 패치 용도)
        ac.app = app
        yield ac

    app.dependency_overrides.clear()
