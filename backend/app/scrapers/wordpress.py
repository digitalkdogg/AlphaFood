import asyncio
from urllib.parse import urlparse, urljoin
import httpx
import feedparser
from bs4 import BeautifulSoup

from app.scrapers.base import BaseAdapter, HEADERS


class WordPressAdapter(BaseAdapter):
    async def fetch_candidate_urls(self) -> list[str]:
        base = self.source.url.rstrip("/")

        # Strategy 1: RSS feed
        urls = await self._try_rss(f"{base}/feed/")
        if urls:
            return urls

        # Strategy 2: WP REST API
        urls = await self._try_wp_rest(base)
        if urls:
            return urls

        # Strategy 3: HTML crawl for recipe links
        return await self._try_html_crawl(base)

    async def _try_rss(self, feed_url: str) -> list[str]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                r = await client.get(feed_url)
                if r.status_code != 200:
                    return []
            feed = await asyncio.get_event_loop().run_in_executor(
                None, feedparser.parse, r.text
            )
            return [e.link for e in feed.entries if hasattr(e, "link")]
        except Exception:
            return []

    async def _try_wp_rest(self, base: str) -> list[str]:
        urls = []
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                for page in range(1, 6):
                    r = await client.get(
                        f"{base}/wp-json/wp/v2/posts",
                        params={"per_page": 100, "page": page},
                    )
                    if r.status_code != 200:
                        break
                    posts = r.json()
                    if not posts:
                        break
                    urls.extend(p.get("link", "") for p in posts if p.get("link"))
        except Exception:
            pass
        return urls

    async def _try_html_crawl(self, base: str) -> list[str]:
        try:
            html = await self.fetch_raw_html(base)
            soup = BeautifulSoup(html, "lxml")
            domain = urlparse(base).netloc
            found = set()
            for a in soup.find_all("a", href=True):
                href = urljoin(base, a["href"])
                parsed = urlparse(href)
                if parsed.netloc == domain and "recipe" in href.lower():
                    found.add(href.split("?")[0].split("#")[0])
            return list(found)
        except Exception:
            return []
