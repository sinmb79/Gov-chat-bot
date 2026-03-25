"""
문서 파서 — 1차 정식 지원 형식:
TXT · MD · DOCX · 텍스트 PDF · HTML
"""
import io
from typing import Optional


def parse_txt(content: bytes, encoding: str = "utf-8") -> str:
    return content.decode(encoding, errors="replace")


def parse_md(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def parse_html(content: bytes) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")
    # script/style 제거
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def parse_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_pdf(content: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
    except Exception:
        return ""


PARSERS = {
    "txt": parse_txt,
    "md": parse_md,
    "html": parse_html,
    "htm": parse_html,
    "docx": parse_docx,
    "pdf": parse_pdf,
}


def extract_text(content: bytes, filename: str) -> Optional[str]:
    """파일 확장자에 따라 적절한 파서 선택."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    parser = PARSERS.get(ext)
    if not parser:
        return None
    try:
        return parser(content)
    except Exception:
        return None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    문단 단위 청킹 (약 chunk_size 토큰).
    overlap: 이전 청크 끝 글자를 다음 청크 시작에 포함.
    """
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_size and current:
            chunk_text_ = "\n".join(current)
            chunks.append(chunk_text_)
            # overlap: 마지막 문단 유지
            if overlap > 0 and current:
                current = [current[-1]]
                current_len = len(current[-1])
            else:
                current = []
                current_len = 0
        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n".join(current))

    return chunks if chunks else [text[:chunk_size]]
