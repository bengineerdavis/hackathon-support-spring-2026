"""Web search via DuckDuckGo — no API key required."""

from ddgs import DDGS


def search_web(query: str, n: int = 5) -> list[dict]:
    """Return top-n results as {title, url, snippet} dicts."""
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=n))
        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in raw]
    except Exception as exc:
        return [{"title": "Search unavailable", "url": "", "snippet": str(exc)}]
