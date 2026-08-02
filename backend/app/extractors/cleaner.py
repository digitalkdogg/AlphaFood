import trafilatura


def extract_text(html: str) -> str:
    result = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    return result or ""
