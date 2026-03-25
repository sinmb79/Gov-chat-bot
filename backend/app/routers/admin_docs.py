"""
문서 관리 API — 편집장(editor) 이상 접근.
POST   /api/admin/documents/upload   — 문서 업로드
POST   /api/admin/documents/{id}/approve — 문서 승인 (is_active=True)
GET    /api/admin/documents          — 문서 목록
DELETE /api/admin/documents/{id}     — 문서 삭제
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_editor, require_admin, get_current_admin
from app.models.admin import AdminUser
from app.models.knowledge import Document
from app.services.document_processor import DocumentProcessor
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/documents", tags=["admin-documents"])


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    is_active: bool
    chunk_count: int
    version: int
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    published_at: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """문서 업로드 → 파싱·임베딩 → VectorDB 저장. is_active=False (승인 대기)."""
    tenant_id = current_user.tenant_id
    content = await file.read()

    # 지원 형식 검사
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    SUPPORTED = {"txt", "md", "html", "htm", "docx", "pdf"}
    if ext not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    # Document 레코드 생성
    published = None
    if published_at:
        try:
            published = datetime.fromisoformat(published_at)
        except ValueError:
            pass

    doc = Document(
        tenant_id=tenant_id,
        filename=file.filename,
        source_type="upload",
        is_active=False,  # 편집장 승인 전
        status="pending",
        published_at=published,
        approved_by=None,
    )
    db.add(doc)
    await db.flush()  # id 확보

    # 문서 처리
    providers = getattr(request.app.state, "providers", {})
    processor = DocumentProcessor(
        embedding_provider=providers.get("embedding"),
        vectordb_provider=providers.get("vectordb"),
        db=db,
    )
    chunk_count = await processor.process(tenant_id, doc, content)

    # 감사 로그
    await log_action(
        db=db,
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="doc.upload",
        target_type="document",
        target_id=doc.id,
        diff={"filename": file.filename, "chunk_count": chunk_count},
    )

    return {"id": doc.id, "filename": doc.filename, "status": doc.status, "chunk_count": chunk_count}


@router.post("/{doc_id}/approve")
async def approve_document(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """문서 승인 → is_active=True."""
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status not in ("processed", "embedding_unavailable"):
        raise HTTPException(status_code=400, detail=f"Cannot approve document with status: {doc.status}")

    doc.is_active = True
    doc.approved_by = current_user.id
    doc.approved_at = datetime.utcnow()
    await db.commit()

    await log_action(
        db=db,
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="doc.approve",
        target_type="document",
        target_id=doc.id,
    )

    return {"id": doc.id, "is_active": True}


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    """문서 목록 조회."""
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == current_user.tenant_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """문서 삭제 (DB + VectorDB)."""
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.tenant_id == tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # VectorDB 청크 삭제
    providers = getattr(request.app.state, "providers", {})
    vectordb = providers.get("vectordb")
    if vectordb:
        processor = DocumentProcessor(
            embedding_provider=providers.get("embedding"),
            vectordb_provider=vectordb,
            db=db,
        )
        await processor.delete(tenant_id, doc_id)

    await db.delete(doc)
    await db.commit()

    await log_action(
        db=db,
        tenant_id=tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="doc.delete",
        target_type="document",
        target_id=doc_id,
    )
