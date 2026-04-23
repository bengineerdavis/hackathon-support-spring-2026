"""Disk-backed cache for Sentry API responses."""

import diskcache
from src.config import DATA_DIR

CACHE_DIR = DATA_DIR.parent / "cache"

# How long each category of response is considered fresh.
TTL_ISSUES = 60 * 60          # 1 hour   — issue list changes as new events arrive
TTL_EVENT = 60 * 60           # 1 hour   — latest event per issue can change
TTL_ATTACHMENT = 60 * 60 * 24  # 24 hours — attachment data is immutable once captured

cache = diskcache.Cache(str(CACHE_DIR))


def clear() -> None:
    count = len(cache)
    cache.clear()
    print(f"Cache cleared: {count} entries removed ({CACHE_DIR})")
