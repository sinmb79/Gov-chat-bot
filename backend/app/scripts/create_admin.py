"""
관리자 계정 초기 생성 스크립트.
사용법: python -m app.scripts.create_admin
"""
import asyncio
import sys


async def main():
    print("=== SmartBot KR 관리자 계정 생성 ===\n")

    tenant_id = input("테넌트 ID (예: dongducheon): ").strip()
    if not tenant_id:
        print("오류: 테넌트 ID를 입력하세요.")
        sys.exit(1)

    email = input("관리자 이메일: ").strip()
    if not email:
        print("오류: 이메일을 입력하세요.")
        sys.exit(1)

    import getpass
    password = getpass.getpass("비밀번호 (8자 이상): ")
    if len(password) < 8:
        print("오류: 비밀번호는 8자 이상이어야 합니다.")
        sys.exit(1)

    from app.core.database import engine, Base
    from app.models.tenant import Tenant, TenantConfig
    from app.models.admin import AdminUser, AdminRole
    from app.core.security import hash_password
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    import uuid

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as db:
        # 테넌트 확인 / 생성
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(id=tenant_id, name=tenant_id, slug=tenant_id)
            db.add(tenant)
            await db.flush()
            config = TenantConfig(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                key="tenant_name",
                value=tenant_id,
            )
            db.add(config)
            print(f"테넌트 생성: {tenant_id}")

        # 관리자 생성
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.tenant_id == tenant_id,
                AdminUser.email == email,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"이미 존재하는 계정입니다: {email}")
        else:
            admin = AdminUser(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                email=email,
                hashed_pw=hash_password(password),
                role=AdminRole.admin,
            )
            db.add(admin)
            print(f"관리자 계정 생성: {email} (role: admin)")

        await db.commit()

    print("\n✅ 완료! 대시보드에서 로그인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
