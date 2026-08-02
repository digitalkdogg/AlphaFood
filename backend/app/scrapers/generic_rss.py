import asyncio
import httpx
import feedparser

from app.scrapers.base import BaseAdapter, HEADERS


class GenericRSSAdapter(BaseAdapter):
    async def fetch_candidate_urls(self) -> list[str]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                r = await client.get(self.source.url)
                r.raise_for_status()
            feed = await asyncio.get_event_loop().run_in_executor(
                None, feedparser.parse, r.text
            )
            return [e.link for e in feed.entries if hasattr(e, "link")]
        except Exception:
            return []
