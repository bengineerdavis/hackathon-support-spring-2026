"""Clone getsentry/sentry-docs and maintain a searchable ChromaDB vector index."""

import re
import subprocess
from pathlib import Path

import chromadb

from src.config import DATA_DIR

DOCS_REPO = "https://github.com/getsentry/sentry-docs"
DOCS_DIR = DATA_DIR.parent / "sentry-docs"
CHROMA_DIR = DATA_DIR.parent / "chroma"
_COLLECTION = "sentry_docs"
_CHUNK_CHARS = 800
_OVERLAP_CHARS = 80


def sync_docs() -> Path:
    """Shallow-clone or fast-forward-pull the sentry-docs repo. Returns local path."""
    DOCS_DIR.parent.mkdir(parents=True, exist_ok=True)
    if (DOCS_DIR / ".git").exists():
        print("Updating sentry-docs...")
        subprocess.run(["git", "-C", str(DOCS_DIR), "pull", "--ff-only"], check=True)
    else:
        print("Cloning sentry-docs (shallow) — this may take a minute...")
        subprocess.run(
            ["git", "clone", "--depth=1", DOCS_REPO, str(DOCS_DIR)],
            check=True,
        )
    return DOCS_DIR


def _clean(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)  # frontmatter
    text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)  # fenced code blocks
    text = re.sub(r"<[A-Za-z][^>]*>.*?</[A-Za-z][^>]*>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[A-Za-z][^>]*/?>", "", text)
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.DOTALL)
    return text.strip()


def _prose_ratio(text: str) -> float:
    """Estimate fraction of lines that are natural-language prose rather than code (0–1)."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    prose = sum(
        1 for l in lines
        if not l.startswith("    ")                    # not indented code
        and not re.match(r"^\s*[`{}\[\]()<>|=]", l)   # not symbol-heavy lines
        and len(l.split()) > 3                         # at least a few words
    )
    return prose / len(lines)


def _split_chunks(text: str) -> list[str]:
    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) > _CHUNK_CHARS and buf:
            chunks.append(buf.strip())
            buf = buf[-_OVERLAP_CHARS:] + "\n\n" + para
        else:
            buf = (buf + "\n\n" + para).lstrip()
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if len(c) > 60]


def build_index(force: bool = False) -> int:
    """Build or refresh the sentry_docs ChromaDB collection. Returns chunk count.

    Uses the existing index if already populated and force=False.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if force:
        try:
            client.delete_collection(_COLLECTION)
        except Exception:
            pass
    collection = client.get_or_create_collection(_COLLECTION)

    if not force and collection.count() > 0:
        print(f"Using existing docs index ({collection.count()} chunks). Pass force=True to rebuild.")
        return collection.count()

    md_files = sorted(DOCS_DIR.rglob("*.md")) + sorted(DOCS_DIR.rglob("*.mdx"))
    print(f"Indexing {len(md_files)} markdown files (this runs once and may take several minutes)...")

    count = 0
    for path in md_files:
        try:
            text = _clean(path.read_text(errors="replace"))
        except Exception:
            continue
        rel = str(path.relative_to(DOCS_DIR))
        for i, chunk in enumerate(_split_chunks(text)):
            collection.upsert(
                ids=[f"{rel}::{i}"],
                documents=[chunk],
                metadatas=[{"source": rel}],
            )
            count += 1

    print(f"Indexed {count} chunks from {len(md_files)} files.")
    return count


def _source_to_url(source: str) -> str | None:
    """Convert a repo-relative source path to its docs.sentry.io URL.

    Only paths under docs/ have corresponding web pages.
    platform-includes/ and other partials are skipped (return None).
    """
    if not source.startswith("docs/"):
        return None
    path = Path(source)
    parts = path.with_suffix("").parts[1:]  # strip leading "docs"
    if not parts:
        return None
    if parts[-1] == "index":
        parts = parts[:-1]
    if not parts:
        return None
    return "https://docs.sentry.io/" + "/".join(parts) + "/"


def search_docs(query: str, n: int = 5) -> list[dict]:
    """Return top-n relevant doc chunks as {text, source, url} dicts.

    Fetches 4× candidates from ChromaDB then re-ranks by prose density so
    written explanations and concepts surface above raw code examples.
    url is the docs.sentry.io page URL, or None for partial/include files.
    Returns [] if the index has not been built yet.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(_COLLECTION)
    except Exception:
        return []
    if collection.count() == 0:
        return []
    fetch = min(n * 4, collection.count())
    results = collection.query(query_texts=[query], n_results=fetch)
    candidates = [
        {
            "text": doc,
            "source": meta["source"],
            "url": _source_to_url(meta["source"]),
            "_prose": _prose_ratio(doc),
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
    candidates.sort(key=lambda c: c["_prose"], reverse=True)
    return [
        {"text": c["text"], "source": c["source"], "url": c["url"]}
        for c in candidates[:n]
    ]
