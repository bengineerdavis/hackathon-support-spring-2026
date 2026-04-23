# Hackathon Plan: Sentry Attachment Log Summarizer

## Goal

Pull raw log attachments from Sentry events, summarize them with a local LLM, persist the results to disk, and present them in a simple GUI.

---

## Architecture

```text
┌─────────────────────┐     ┌──────────────────────┐
│  event_generator.py │────▶│  Sentry Project       │
│  (sentry_sdk)       │     │  (captures events +   │
│                     │     │   raw log attachments) │
└─────────────────────┘     └──────────┬───────────┘
                                        │ REST API
                            ┌──────────▼───────────┐
                            │  sentry_client.py     │
                            │  - list_events()      │
                            │  - list_attachments() │
                            │  - download()         │
                            └──────────┬───────────┘
                                        │
                            ┌──────────▼───────────┐
                            │  summarizer.py        │
                            │  - llm library        │
                            │  - structured prompt  │
                            └──────────┬───────────┘
                                        │
                            ┌──────────▼───────────┐
                            │  storage.py           │
                            │  data/events/         │
                            │   {event_id}/         │
                            │     summary.json      │
                            │     attachments/      │
                            └──────────┬───────────┘
                                        │
                            ┌──────────▼───────────┐
                            │  app.py (Streamlit)   │
                            │  - event list sidebar │
                            │  - raw ↔ summary view │
                            └───────────────────────┘
```

---

## File Structure

```text
hackathon-support-spring-2026/
├── plan.md
├── idea.md
├── mise.toml
├── pyproject.toml
├── .env.example
├── src/
│   ├── config.py           # env var loading
│   ├── sentry_client.py    # Sentry REST API wrapper
│   ├── event_generator.py  # creates fake events with log attachments
│   ├── summarizer.py       # llm-based summarization
│   ├── storage.py          # disk I/O for summaries + raw attachments
│   └── app.py              # Streamlit GUI
├── tests/
│   ├── test_sentry_client.py
│   ├── test_summarizer.py
│   └── test_storage.py
└── data/
    └── events/             # auto-created; one dir per event_id
```

---

## Step-by-Step Implementation

### 1. Environment Setup

Requires [mise](https://mise.jdx.dev) and [uv](https://docs.astral.sh/uv/) on your PATH.

```bash
mise run setup                # creates .venv and installs all deps via uv
mise run install-model-plugin # registers llm-ollama plugin with llm

# Install Ollama (https://ollama.com) and pull a model:
ollama pull llama3
```

Copy `.env.example` → `.env` and fill in:

- `SENTRY_AUTH_TOKEN` — personal auth token with `project:read` + `event:read`
- `SENTRY_ORG_SLUG` — your org slug
- `SENTRY_PROJECT_SLUG` — your project slug
- `SENTRY_DSN` — your project DSN (for event_generator)
- `LLM_MODEL` — model key for the `llm` library (default: `ollama/llama3`)

### 2. Generate Fake Events

```bash
mise run generate-events
```

Creates 3 fake exception events, each with a `.log` attachment containing realistic multi-line raw log data (timestamps, log levels, stack traces).

### 3. Pull + Summarize

```bash
mise run pipeline
```

Iterates all project events, downloads each attachment, sends it to the local LLM via the `llm` library, and writes output to `data/events/`. Already-summarized attachments are skipped.

### 4. Launch GUI

```bash
mise run app
```

Opens a browser with:

- Left sidebar: list of events (title + timestamp)
- Main panel: LLM summary (formatted) + expandable raw log

### 5. Run Tests

```bash
mise run test
```

---

## Data Schema

`data/events/{event_id}/summary.json`:

```json
{
  "event_id": "abc123",
  "title": "ZeroDivisionError: division by zero",
  "timestamp": "2026-04-21T10:00:00Z",
  "attachments": [
    {
      "attachment_id": "1",
      "filename": "app.log",
      "summary": "The application encountered a ZeroDivisionError...",
      "raw_path": "attachments/app.log"
    }
  ]
}
```

---

## Testing Strategy

- **Unit tests** use `pytest` + `responses` to mock all HTTP calls
- `test_sentry_client.py` — verifies event listing, attachment listing, and download
- `test_summarizer.py` — mocks the `llm` model, checks prompt construction and output
- `test_storage.py` — verifies disk writes, directory structure, and JSON schema

Run: `mise run test`

---

## Dependencies

| Package | Purpose |
| --- | --- |
| `sentry-sdk` | generate fake events |
| `requests` | Sentry REST API calls |
| `python-dotenv` | env var loading |
| `llm` + `llm-ollama` | local LLM summarization via llm.datasette.io |
| `streamlit` | GUI |
| `pytest` + `responses` | testing |
