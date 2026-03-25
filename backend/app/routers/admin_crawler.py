"""
크롤러 관리 API.
POST /api/admin/crawler/urls         — URL 등록
GET  /api/admin/crawler/urls         — URL 목록
POST /api/admin/crawler/run/{url_id} — 수동 크롤링 실행
DELETE /api/admin/crawler/urls/{id}  — URL 삭제
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_editor
from app.models.admin import AdminUser
from app.models.knowledge import CrawlerURL, Document
from app.services.crawler import CrawlerService
from app.services.document_processor import DocumentProcessor
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/crawler", tags=["admin-crawler"])


class CrawlerURLCreate(BaseModel):
    url: str
    url_type: str = "page"
    interval_hours: int = 24


class CrawlerURLOut(BaseModel):
    id: str
    url: str
    url_type: str
    interval_hours: int
    is_active: bool
    last_crawled: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/urls", status_code=status.HTTP_201_CREATED)
async def register_url(
    body: CrawlerURLCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """크롤러 URL 등록."""
    crawler_url = CrawlerURL(
        tenant_id=current_user.tenant_id,
        url=body.url,
        url_type=body.url_type,
        interval_hours=body.interval_hours,
        is_active=True,
    )
    db.add(crawler_url)
    await db.commit()
    await db.refresh(crawler_url)

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="crawler.approve",
        target_type="crawler_url",
        target_id=crawler_url.id,
        diff={"url": body.url},
    )

    return {"id": crawler_url.id, "url": crawler_url.url}


@router.get("/urls", response_model=list[CrawlerURLOut])
async def list_urls(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    result = await db.execute(
        select(CrawlerURL).where(CrawlerURL.tenant_id == current_user.tenant_id)
    )
    return result.scalars().all()


@router.post("/run/{url_id}")
async def run_crawl(
    url_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    """수동 크롤링 실행 → 텍스트 추출 → 문서로 저장."""
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(CrawlerURL).where(CrawlerURL.id == url_id, CrawlerURL.tenant_id == tenant_id)
    )
    crawler_url = result.scalar_one_or_none()
    if not crawler_url:
        raise HTTPException(status_code=404, detail="Crawler URL not found")

    service = CrawlerService(db)
    text = await service.run(crawler_url, tenant_id)

    if not text:
        raise HTTPException(status_code=422, detail="Failed to crawl or robots.txt disallowed")

    # 크롤링 결과를 문서로 저장
    from urllib.parse import urlparse
    parsed = urlparse(crawler_url.url)
    filename = parsed.netloc + parsed.path.replace("/", "_") + ".txt"

    doc = Document(
        tenant_id=tenant_id,
        filename=filename,
        source_type="crawler",
        source_url=crawler_url.url,
        is_active=False,  # 편집장 검토 후 승인
        status="pending",
    )
    db.add(doc)
    await db.flush()

    providers = getattr(request.app.state, "providers", {})
    processor = DocumentProcessor(
        embedding_provider=providers.get("embedding"),
        vectordb_provider=providers.get("vectordb"),
        db=db,
    )
    chunk_count = await processor.process(tenant_id, doc, text.encode("utf-8"))

    return {
        "doc_id": doc.id,
        "url": crawler_url.url,
        "chunk_count": chunk_count,
        "status": doc.status,
    }


@router.delete("/urls/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    url_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_editor),
):
    result = await db.execute(
        select(CrawlerURL).where(CrawlerURL.id == url_id, CrawlerURL.tenant_id == current_user.tenant_id)
    )
    crawler_url = result.scalar_one_or_none()
    if not crawler_url:
        raise HTTPException(status_code=404, detail="Crawler URL not found")

    await db.delete(crawler_url)
    await db.commit()

    await log_action(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type="admin_user",
        action="crawler.reject",
        target_type="crawler_url",
        target_id=url_id,
    )
