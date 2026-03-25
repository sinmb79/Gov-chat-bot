"""
웹 크롤러 — httpx + BeautifulSoup4.
robots.txt 준수. CrawlerURL 기반.
"""
from typing import Optional
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import CrawlerURL, Document


CRAWLER_HEADERS = {
    "User-Agent": "SmartBot-KR/1.0 (+https://github.com/sinmb79/Gov-chat-bot)",
}
CRAWL_TIMEOUT = 15  # 초


async def check_robots_txt(base_url: str, target_path: str) -> bool:
    """robots.txt 확인. 크롤링 허용 여부 반환."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(robots_url, headers=CRAWLER_HEADERS)
            if resp.status_code != 200:
                return True  # robots.txt 없으면 허용으로 간주
            content = resp.text.lower()
            # 간단한 User-agent: * Disallow 체크
            lines = content.splitlines()
            in_block = False
            for line in lines:
                line = line.strip()
                if line.startswith("user-agent:"):
                    agent = line.split(":", 1)[1].strip()
                    in_block = agent in ("*", "smartbot-kr")
                elif in_block and line.startswith("disallow:"):
                    disallowed = line.split(":", 1)[1].strip()
                    if disallowed and target_path.startswith(disallowed):
                        return False
            return True
    except Exception:
        return True  # 확인 불가 시 허용


async def crawl_url(url: str) -> Optional[str]:
    """URL 크롤링 → 텍스트 추출. 실패 시 None."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        target_path = parsed.path or "/"

        if not await check_robots_txt(url, target_path):
            return None  # robots.txt 불허

        async with httpx.AsyncClient(
            timeout=CRAWL_TIMEOUT,
            follow_redirects=True,
            headers=CRAWLER_HEADERS,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type:
            soup = BeautifulSoup(resp.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        else:
            return resp.text

    except Exception:
        return None


class CrawlerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, crawler_url: CrawlerURL, tenant_id: str) -> Optional[str]:
        """크롤러 URL 실행 → 텍스트 반환."""
        text = await crawl_url(crawler_url.url)

        # last_crawled 업데이트
        crawler_url.last_crawled = datetime.now(timezone.utc)
        await self.db.commit()

        return text
