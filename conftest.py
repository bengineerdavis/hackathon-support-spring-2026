import os
import pytest
import diskcache

# Set test defaults before any src module is imported during collection.
os.environ.setdefault("SENTRY_AUTH_TOKEN", "test-token")
os.environ.setdefault("SENTRY_ORG_SLUG", "my-org")
os.environ.setdefault("SENTRY_PROJECT_SLUG", "my-project")
os.environ.setdefault("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
os.environ.setdefault("SENTRY_BASE_URL", "https://sentry.io")
os.environ.setdefault("LLM_MODEL", "ollama/llama3")


@pytest.fixture(autouse=True)
def fresh_cache(tmp_path, monkeypatch):
    """Give every test its own empty cache so nothing bleeds between runs."""
    test_cache = diskcache.Cache(str(tmp_path / "cache"))
    import src.cache as sc
    monkeypatch.setattr(sc, "cache", test_cache)
    yield test_cache
    test_cache.close()
