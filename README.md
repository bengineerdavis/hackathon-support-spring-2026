# Sentry Error Attachment Summarizer

Pulls raw file attachments from Sentry error events, summarizes them per event with a local LLM, and presents an AI-generated analysis in a two-page Streamlit UI. A built-in research tool cross-references each issue against the Sentry Help Center, sentry-docs (local vector index), and the web.

---

## Prerequisites

| Tool | Install |
| --- | --- |
| [mise](https://mise.jdx.dev) | `curl https://mise.run \| sh` |
| [Ollama](https://ollama.com) | Download from ollama.com |

---

## First-time setup

**1. Enter the directory** — mise auto-syncs dependencies:

```bash
cd hackathon-support-spring-2026
```

**2. Install the Ollama plugin for the `llm` library:**

```bash
mise run install-model-plugin
```

**3. Pull your LLM model** (or substitute any model Ollama supports):

```bash
ollama pull llama3
```

**4. Configure your environment:**

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Value |
| --- | --- |
| `SENTRY_AUTH_TOKEN` | Settings → Auth Tokens → Create token (needs `project:read` + `event:read`) |
| `SENTRY_ORG_SLUG` | Your org slug from the Sentry URL, e.g. `my-company` |
| `SENTRY_PROJECT_SLUG` | Your project slug, e.g. `python-backend` |
| `SENTRY_BASE_URL` | `https://us.sentry.io` (US) or `https://de.sentry.io` (EU) |
| `SENTRY_DSN` | Project Settings → Client Keys — only needed for `generate-events` |
| `LLM_MODEL` | Model key for the `llm` library, e.g. `ollama/llama3` or `qwen3.5:9b` |

**5. Verify token access:**

```bash
mise run check-access
```

```
Sentry API token permissions:
  ✓ project:read  — list issues in the project
  ✓ event:read    — fetch events and download attachments
```

**6. Run the pipeline:**

```bash
mise run pipeline
```

Fetches all issues, downloads every attachment per event, and summarizes them together in one LLM prompt. Results are saved under `data/events/`. Already-processed events are skipped.

**7. Launch the UI:**

```bash
mise run app
```

---

## The UI

**Main page** — lists every captured issue with a one-sentence summary. Click **View issue →** to open the detail page.

**Issue page** — shows the full summary, expandable raw attachment files, the Sentry link (or trace view if tracing is enabled), and a Research panel. Use the sidebar to jump directly to another issue or return to the main list.

---

## Refreshing data

| Goal | Command |
| --- | --- |
| Fetch new issues, skip already-summarized | `mise run pipeline` |
| Force re-fetch all from Sentry + research new | `mise run refresh` |
| Full reset: clear cache, re-summarize everything, re-research all | `mise run refresh-all` |
| Clear the API response cache only | `mise run clear-cache` |

---

## Research (optional enrichment)

The research panel on each issue page searches three sources:

- **Sentry Help Center** — public Zendesk search, no API key needed
- **Sentry docs** — local ChromaDB vector index built from `getsentry/sentry-docs`
- **Web search** — DuckDuckGo, no API key needed

Past research sessions are embedded and stored in ChromaDB so similar future queries surface related prior work.

**Build the docs index** (one-time, ~10 minutes — shallow clone of sentry-docs):

```bash
mise run index-docs
```

**Research all summarized issues:**

```bash
mise run research
```

Results are cached. Click **Research this issue** in the UI to run on demand for a single issue.

---

## Seeding test events

If you don't have real Sentry events yet:

```bash
mise run generate-events
```

Sends 3 Python exception events (ZeroDivisionError, KeyError, TypeError) each with a raw `.log` attachment. Run `mise run pipeline` afterwards to summarize them.

---

## Development

```bash
mise run test        # full test suite — no .env or Ollama needed
```

### Project structure

```
src/
  app.py                     main index page (Streamlit)
  pages/
    issue.py                 issue detail page (Streamlit)
  config.py                  env var loading
  sentry_client.py           Sentry REST API + pagination + caching
  summarizer.py              LLM summarization + pipeline orchestration
  storage.py                 writes summary.json + raw attachment bytes
  research.py                orchestrates Help Center / docs / web searches
  docs_index.py              clones sentry-docs, builds ChromaDB vector index
  zendesk_client.py          Sentry Help Center search (public API)
  web_search.py              DuckDuckGo search
  kapa_client.py             (reserved)
  cache.py                   diskcache wrapper for API response caching
  event_generator.py         sends fake events to Sentry for testing
  prompts/
    summarize_system.txt     LLM system prompt
    summarize_user.txt       LLM user prompt template
    summarize_attachment_block.txt  per-attachment block template

data/
  events/{event_id}/
    summary.json             see schema below
    attachments/             raw attachment files
  research/{event_id}.json   cached research session
  chroma/                    ChromaDB vector store (docs + session embeddings)
  sentry-docs/               shallow clone of getsentry/sentry-docs

tests/
  test_sentry_client.py
  test_summarizer.py
  test_storage.py
```

### Data schema

`data/events/{event_id}/summary.json`:

```json
{
  "event_id": "abc123",
  "issue_id": "7437259900",
  "trace_id": "",
  "title": "ZeroDivisionError: division by zero",
  "timestamp": "2026-04-21T10:00:00Z",
  "summary": "The application crashed while calculating a discount...",
  "attachments": [
    {
      "attachment_id": "1",
      "filename": "app.log",
      "raw_path": "data/events/abc123/attachments/app.log"
    }
  ]
}
```

`data/research/{event_id}.json`:

```json
{
  "session_id": "uuid",
  "event_id": "abc123",
  "issue_id": "7437259900",
  "title": "ZeroDivisionError: division by zero",
  "timestamp": "2026-04-21T10:05:00Z",
  "help_results": [{ "title": "...", "url": "...", "snippet": "..." }],
  "doc_results":  [{ "text": "...", "source": "docs/..." }],
  "web_results":  [{ "title": "...", "url": "...", "snippet": "..." }],
  "similar_sessions": [{ "event_id": "...", "title": "...", "session_id": "..." }]
}
```
