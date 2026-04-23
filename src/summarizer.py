"""Summarize raw log attachments using the `llm` library (llm.datasette.io)."""

from pathlib import Path
import llm
from src.config import LLM_MODEL

_PROMPTS_DIR = Path(__file__).parent / "prompts"

def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text()

_MAX_CHARS_PER_ATTACHMENT = 6000


def summarize(attachments: list[tuple[str, str]], title: str = "") -> str:
    """Return a single plain-language summary covering all attachments for one event.

    Each entry in `attachments` is a (filename, text_content) tuple.
    """
    attachment_block = _load_prompt("summarize_attachment_block.txt")
    blocks = "\n\n".join(
        attachment_block.format(filename=fn, content=content[:_MAX_CHARS_PER_ATTACHMENT])
        for fn, content in attachments
    )
    prompt = _load_prompt("summarize_user.txt").format(
        title=title or "(unknown)",
        count=len(attachments),
        attachment_blocks=blocks,
    )
    model = llm.get_model(LLM_MODEL)
    response = model.prompt(prompt, system=_load_prompt("summarize_system.txt"))
    return response.text().strip()


def run_pipeline(force_refresh: bool = False) -> None:
    """Fetch all Sentry issues, summarize attachments from the latest event, save to disk.

    Set force_refresh=True to bypass the disk cache and re-fetch all API data.
    """
    from src.sentry_client import assert_permissions, iter_all_issues, get_latest_event, list_attachments, download_attachment
    from src.storage import save_summary, event_already_summarized, patch_issue_id

    assert_permissions()
    issues = iter_all_issues(force_refresh=force_refresh)
    print(f"Processing {len(issues)} issues...")

    for issue in issues:
        issue_id = issue["id"]
        title = issue.get("title", "")

        latest = get_latest_event(issue_id, force_refresh=force_refresh)
        event_id = latest["id"]
        timestamp = latest.get("dateCreated", issue.get("lastSeen", ""))

        if event_already_summarized(event_id):
            patch_issue_id(event_id, issue_id)
            print(f"  Skipping {event_id} (already summarized)")
            continue

        attachment_meta = list_attachments(event_id, force_refresh=force_refresh)
        if not attachment_meta:
            print(f"  Skipping {event_id} (no attachments)")
            continue

        attachment_texts: list[tuple[str, str]] = []
        raw_attachments: list[dict] = []

        for att in attachment_meta:
            att_id = str(att["id"])
            filename = att.get("name", "attachment")
            raw = download_attachment(event_id, att_id, force_refresh=force_refresh)
            text = raw.decode("utf-8", errors="replace")
            attachment_texts.append((filename, text))
            raw_attachments.append({"attachment_id": att_id, "filename": filename, "raw": raw})

        trace_id = (latest.get("contexts") or {}).get("trace", {}).get("trace_id", "")

        print(f"  Summarizing issue {issue_id} / event {event_id} ({len(attachment_texts)} attachment(s))...")
        summary_text = summarize(attachment_texts, title=title)

        save_summary(event_id, title, timestamp, summary_text, raw_attachments, issue_id=issue_id, trace_id=trace_id)

    print("Pipeline complete.")


if __name__ == "__main__":
    import sys
    run_pipeline(force_refresh="--force-refresh" in sys.argv)
