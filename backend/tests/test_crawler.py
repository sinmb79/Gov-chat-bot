"""
크롤러 서비스 단위 테스트.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.crawler import crawl_url, check_robots_txt, CrawlerService
from app.services.parsers.text_parser import extract_text


@pytest.mark.asyncio
async def test_crawl_url_extracts_text():
    """정상 HTML 응답 → 텍스트 추출."""
    html_str = "<html><body><p>동두천시 여권 안내</p><script>bad()</script></body></html>"
    html = html_str.encode("utf-8")

    mock_response = MagicMock()
    mock_response.content = html
    mock_response.text = html_str
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.crawler.check_robots_txt", return_value=True), \
         patch("httpx.AsyncClient", return_value=mock_client):
        result = await crawl_url("https://www.example.com/guide")

    assert result is not None
    assert "동두천시" in result
    assert "bad()" not in result


@pytest.mark.asyncio
async def test_crawl_url_returns_none_on_robots_disallow():
    """robots.txt 불허 → None 반환."""
    with patch("app.services.crawler.check_robots_txt", return_value=False):
        result = await crawl_url("https://www.example.com/private")

    assert result is None


@pytest.mark.asyncio
async def test_crawl_url_returns_none_on_network_error():
    """네트워크 오류 → None 반환 (예외 미전파)."""
    import httpx
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch("app.services.crawler.check_robots_txt", return_value=True), \
         patch("httpx.AsyncClient", return_value=mock_client):
        result = await crawl_url("https://unreachable.example.com")

    assert result is None


@pytest.mark.asyncio
async def test_crawler_service_updates_last_crawled():
    """run() 후 last_crawled 업데이트."""
    db = AsyncMock()
    db.commit = AsyncMock()

    crawler_url = MagicMock()
    crawler_url.url = "https://www.example.com"
    crawler_url.last_crawled = None

    with patch("app.services.crawler.crawl_url", return_value="크롤링된 내용"):
        service = CrawlerService(db)
        result = await service.run(crawler_url, "tenant-1")

    assert result == "크롤링된 내용"
    assert crawler_url.last_crawled is not None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_crawler_service_returns_none_on_fail():
    """크롤링 실패 → None 반환."""
    db = AsyncMock()
    crawler_url = MagicMock()
    crawler_url.url = "https://fail.example.com"

    with patch("app.services.crawler.crawl_url", return_value=None):
        service = CrawlerService(db)
        result = await service.run(crawler_url, "tenant-1")

    assert result is None
