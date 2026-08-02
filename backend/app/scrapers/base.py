from abc import ABC, abstractmethod
import httpx
from app.models import Source

HEADERS = {
    "User-Agent": "AlphaFood-Bot/1.0 (+https://alphafood.app; recipe aggregator for alpha-gal syndrome)"
}


class BaseAdapter(ABC):
    def __init__(self, source: Source):
        self.source = source

    @abstractmethod
    async def fetch_candidate_urls(self) -> list[str]:
        ...

    async def fetch_raw_html(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=30
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
