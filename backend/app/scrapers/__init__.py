from .wordpress import WordPressAdapter
from .generic_rss import GenericRSSAdapter
from .html_sitemap import HTMLSitemapAdapter
from .single_page import SinglePageAdapter
from app.models import Source

ADAPTER_MAP = {
    "wordpress": WordPressAdapter,
    "generic_rss": GenericRSSAdapter,
    "html_sitemap": HTMLSitemapAdapter,
    "single_page": SinglePageAdapter,
}


def get_adapter(source: Source):
    cls = ADAPTER_MAP.get(source.scraper_type.value)
    if not cls:
        raise ValueError(f"Unknown scraper type: {source.scraper_type}")
    return cls(source)
