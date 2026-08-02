from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import BaseAdapter, HEADERS


class HTMLSitemapAdapter(BaseAdapter):
    async def fetch_candidate_urls(self) -> list[str]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                r = await client.get(self.source.url)
                r.raise_for_status()
                content_type = r.headers.get("content-type", "")

            url_lower = self.source.url.lower()
            if "xml" in content_type or url_lower.endswith(".xml"):
                return self._parse_sitemap(r.text)
            return self._parse_html(r.text, self.source.url)
        except Exception:
            return []

    def _parse_sitemap(self, xml: str) -> list[str]:
        soup = BeautifulSoup(xml, "lxml-xml")
        return [loc.get_text(strip=True) for loc in soup.find_all("loc")]

    def _parse_html(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        domain = urlparse(base_url).netloc
        found = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc == domain:
                found.add(href.split("?")[0].split("#")[0])
        return list(found)
