"""
관리자 인증 API.
POST /api/admin/auth/login — 로그인 (JWT 발급)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_admin_token
from app.models.admin import AdminUser

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    tenant_id: str
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.tenant_id == body.tenant_id,
            AdminUser.email == body.email,
            AdminUser.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    token = create_admin_token(user.id, user.tenant_id, user.role.value)
    return LoginResponse(access_token=token, role=user.role.value)
