from app.scrapers.base import BaseAdapter


class SinglePageAdapter(BaseAdapter):
    async def fetch_candidate_urls(self) -> list[str]:
        return [self.source.url]
