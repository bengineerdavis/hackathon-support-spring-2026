"""Search Sentry's public Zendesk Help Center — no authentication required."""

import re

import requests

_BASE = "https://sentry.zendesk.com/api/v2/help_center"


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def search_help(query: str, n: int = 5) -> list[dict]:
    """Return top-n help articles as {title, url, snippet} dicts."""
    resp = requests.get(
        f"{_BASE}/articles/search.json",
        params={"query": query, "locale": "en-us", "per_page": n},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("html_url", ""),
            "snippet": _strip_html(r.get("snippet") or r.get("body", "")[:800]),
        }
        for r in resp.json().get("results", [])
    ]
