"""Orchestrate multi-source research for a Sentry issue and persist sessions.

Each session captures:
  - Relevant sentry-docs chunks (vector search against local index)
  - Sentry Help Center articles (public Zendesk search API, no auth)
  - Web search results (DuckDuckGo)
  - References to similar past sessions (vector similarity on session embeddings)

Sessions are stored as JSON under data/research/ and their embeddings are kept in a
separate ChromaDB collection so future queries can reuse relevant prior work.
"""

import json
import re as _re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from src.config import DATA_DIR

_SESSIONS_DIR = DATA_DIR.parent / "research"
_CHROMA_DIR = DATA_DIR.parent / "chroma"
_SESSIONS_COLLECTION = "research_sessions"

_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def _session_path(event_id: str) -> Path:
    return _SESSIONS_DIR / f"{event_id}.json"


def load_session(event_id: str) -> dict | None:
    """Return the cached research session for an event, or None."""
    path = _session_path(event_id)
    return json.loads(path.read_text()) if path.exists() else None


def _save_session(session: dict) -> None:
    _session_path(session["event_id"]).write_text(json.dumps(session, indent=2))
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    col = client.get_or_create_collection(_SESSIONS_COLLECTION)
    col.upsert(
        ids=[session["session_id"]],
        documents=[session["_embedding_text"]],
        metadatas={
            "event_id": session["event_id"],
            "issue_id": session.get("issue_id", ""),
            "title": session.get("title", ""),
        },
    )


# ---------------------------------------------------------------------------
# Similarity search over past sessions
# ---------------------------------------------------------------------------

def find_similar_sessions(query: str, n: int = 3) -> list[dict]:
    """Return up to n past sessions whose topics are most similar to query."""
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    try:
        col = client.get_collection(_SESSIONS_COLLECTION)
    except Exception:
        return []
    total = col.count()
    if total == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(n, total))
    sessions = []
    for meta in results["metadatas"][0]:
        s = load_session(meta["event_id"])
        if s:
            sessions.append(s)
    return sessions


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def research_issue(
    event_id: str,
    issue_id: str,
    title: str,
    summary: str,
    force: bool = False,
) -> dict:
    """Run docs/web/kapa research for a Sentry issue and cache the result.

    On subsequent calls with the same event_id, returns the cached session unless
    force=True. Similar past sessions are surfaced as context without re-running
    their searches.
    """
    if not force:
        cached = load_session(event_id)
        if cached:
            return cached

    from src.docs_index import search_docs
    from src.web_search import search_web
    from src.zendesk_client import search_help

    embedding_text = f"{title}\n{summary}"
    similar = find_similar_sessions(embedding_text)

    error_class = title.split(":")[0].strip()
    # Pull the "What happened" line from structured AI summary for targeted queries
    _wh = _re.search(r"\*\*What happened:\*\*\s*(.+?)(?:\n|$)", summary)
    what_happened = _wh.group(1).strip() if _wh else summary[:200]

    doc_results = search_docs(f"{title} {summary[:600]}")
    web_results = search_web(f"{error_class}: {what_happened}", n=5)
    help_results = search_help(f"{title} {what_happened}", n=5)

    session = {
        "session_id": str(uuid.uuid4()),
        "event_id": event_id,
        "issue_id": issue_id,
        "title": title,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "doc_results": doc_results,
        "web_results": web_results,
        "help_results": help_results,
        "similar_sessions": [
            {
                "event_id": s["event_id"],
                "title": s["title"],
                "session_id": s["session_id"],
            }
            for s in similar
            if s["event_id"] != event_id
        ],
        "_embedding_text": embedding_text,
    }
    _save_session(session)
    return session


# ---------------------------------------------------------------------------
# CLI: research every summarized event
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    force = "--force-refresh" in sys.argv
    from src.storage import load_all_summaries

    summaries = load_all_summaries()
    if not summaries:
        print("No summaries found. Run the pipeline first.")
    else:
        for ev in summaries:
            print(f"{'Re-researching' if force else 'Researching'} {ev['event_id']} — {ev['title'][:60]}")
            research_issue(
                event_id=ev["event_id"],
                issue_id=ev.get("issue_id", ""),
                title=ev["title"],
                summary=ev.get("summary", ""),
                force=force,
            )
        print("Done.")
