"""
문서 처리 파이프라인:
파싱 → 청킹 → 임베딩 → VectorDB 저장 → Document 레코드 업데이트
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document
from app.providers.embedding import EmbeddingProvider
from app.providers.vectordb import VectorDBProvider
from app.services.parsers.text_parser import extract_text, chunk_text


class DocumentProcessor:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vectordb_provider: VectorDBProvider,
        db: AsyncSession,
    ):
        self.embedding = embedding_provider
        self.vectordb = vectordb_provider
        self.db = db

    async def process(self, tenant_id: str, doc: Document, content: bytes) -> int:
        """
        문서를 파싱·청킹·임베딩하여 VectorDB에 저장.
        chunk_count 반환. 실패 시 0.
        """
        # 1. 텍스트 추출
        text = extract_text(content, doc.filename)
        if not text or not text.strip():
            doc.status = "parse_failed"
            await self.db.commit()
            return 0

        # 2. 청킹
        chunks = chunk_text(text)
        if not chunks:
            doc.status = "parse_failed"
            await self.db.commit()
            return 0

        # 3. 임베딩
        try:
            embeddings = await self.embedding.embed(chunks)
        except NotImplementedError:
            doc.status = "embedding_unavailable"
            await self.db.commit()
            return 0
        except Exception:
            doc.status = "embedding_failed"
            await self.db.commit()
            return 0

        # 4. 메타데이터 구성
        published = doc.published_at.strftime("%Y.%m") if doc.published_at else ""
        metadatas = [
            {
                "doc_id": doc.id,
                "filename": doc.filename,
                "chunk_idx": i,
                "published_at": published,
                "tenant_id": tenant_id,
            }
            for i in range(len(chunks))
        ]

        # 5. VectorDB 저장
        await self.vectordb.upsert(
            tenant_id=tenant_id,
            doc_id=doc.id,
            chunks=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        # 6. Document 레코드 업데이트
        doc.chunk_count = len(chunks)
        doc.status = "processed"
        await self.db.commit()

        return len(chunks)

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        """VectorDB에서 문서 청크 삭제."""
        await self.vectordb.delete(tenant_id=tenant_id, doc_id=doc_id)
