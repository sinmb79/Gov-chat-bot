"""
FAQ CRUD API — 편집장(editor) 이상.
POST   /api/admin/faqs           — FAQ 생성
GET    /api/admin/faqs           — FAQ 목록
PUT    /api/admin/faqs/{id}      — FAQ 수정
DELETE /api/admin/faqs/{id}      — FAQ 삭제
POST   /api/admin/faqs/{id}/index — FAQ 벡터 색인
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_editor, get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import FAQ
from app.services.audit import log_action
from app.services.faq_search import FAQSearchService

router = APIRouter(prefix="/api/admin/faqs", tags=["admin-faq"])


class FAQCreate(BaseModel):
    category: Optional[str] = None
    question: str
    answer: str
    keywords: Optional[list[str]] = None


class FAQUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    keywords: Optional[list[str]] = None
    is_active: Optional[bool] = None


class FAQOut(BaseModel):
    id: str
    category: Optional[str] = None
    question: str
    answer: str
    keywords: Optional[list] = None
    hit_count: int
    is_active: bool

    class Config:
        from_attributes = True


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FAQOut)
async def create_faq(
    body: FAQCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    faq = FAQ(
        tenant_id=current_user.tenant_id,
        category=body.category,
        question=body.question,
        answer=body.answer,
        keywords=body.keywords,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(faq)
    await db.flush()

    # 벡터 색인
    providers = getattr(request.app.state, "providers", {})
    if providers.get("embedding") and providers.get("vectordb"):
        service = FAQSearchService(providers["embedding"], providers["vectordb"], db)
        try:
            await service.index_faq(current_user.tenant_id, faq)
        except Exception:
            pass  # 색인 실패해도 FAQ 저장은 성공

    await db.commit()
    await db.refresh(faq)

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="faq.create",
        target_type="faq",
        target_id=faq.id,
        diff={"question": body.question},
    )
    return faq


@router.get("", response_model=list[FAQOut])
async def list_faqs(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    result = await db.execute(
        select(FAQ)
        .where(FAQ.tenant_id == current_user.tenant_id)
        .order_by(FAQ.created_at.desc())
    )
    return result.scalars().all()


@router.put("/{faq_id}", response_model=FAQOut)
async def update_faq(
    faq_id: str,
    body: FAQUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    result = await db.execute(
        select(FAQ).where(FAQ.id == faq_id, FAQ.tenant_id == current_user.tenant_id)
    )
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    diff = {}
    if body.question is not None:
        diff["question"] = {"before": faq.question, "after": body.question}
        faq.question = body.question
    if body.answer is not None:
        diff["answer"] = "updated"
        faq.answer = body.answer
    if body.category is not None:
        faq.category = body.category
    if body.keywords is not None:
        faq.keywords = body.keywords
    if body.is_active is not None:
        faq.is_active = body.is_active

    # 재색인
    providers = getattr(request.app.state, "providers", {})
    if providers.get("embedding") and providers.get("vectordb") and faq.is_active:
        service = FAQSearchService(providers["embedding"], providers["vectordb"], db)
        try:
            await service.index_faq(current_user.tenant_id, faq)
        except Exception:
            pass

    await db.commit()
    await db.refresh(faq)

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="faq.update",
        target_type="faq",
        target_id=faq_id,
        diff=diff,
    )
    return faq


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    result = await db.execute(
        select(FAQ).where(FAQ.id == faq_id, FAQ.tenant_id == current_user.tenant_id)
    )
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    await db.delete(faq)
    await db.commit()

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="faq.delete",
        target_type="faq",
        target_id=faq_id,
    )
