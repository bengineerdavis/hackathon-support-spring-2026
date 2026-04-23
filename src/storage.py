"""Persist event summaries and raw attachment bytes to the local filesystem."""

import json
from pathlib import Path
from src.config import DATA_DIR


def _event_dir(event_id: str) -> Path:
    d = DATA_DIR / event_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_summary(
    event_id: str,
    title: str,
    timestamp: str,
    summary: str,
    attachments: list[dict],
    issue_id: str = "",
    trace_id: str = "",
) -> Path:
    """Write summary.json and raw attachment files for one event.

    `summary` is a single aggregated string covering all attachments.
    Each entry in `attachments` must have keys: attachment_id, filename, raw (bytes).
    `issue_id` is stored so the UI can build a direct link to the Sentry issue page.
    """
    event_dir = _event_dir(event_id)
    att_dir = event_dir / "attachments"
    att_dir.mkdir(exist_ok=True)

    attachment_records = []
    for att in attachments:
        raw_path = att_dir / att["filename"]
        raw_path.write_bytes(att["raw"])
        attachment_records.append({
            "attachment_id": att["attachment_id"],
            "filename": att["filename"],
            "raw_path": str(raw_path.relative_to(DATA_DIR.parent.parent)),
        })

    payload = {
        "event_id": event_id,
        "issue_id": issue_id,
        "trace_id": trace_id,
        "title": title,
        "timestamp": timestamp,
        "summary": summary,
        "attachments": attachment_records,
    }

    summary_file = event_dir / "summary.json"
    summary_file.write_text(json.dumps(payload, indent=2))
    return summary_file


def patch_issue_id(event_id: str, issue_id: str) -> None:
    """Write issue_id into an existing summary.json if the field is missing or empty."""
    summary_file = DATA_DIR / event_id / "summary.json"
    if not summary_file.exists():
        return
    data = json.loads(summary_file.read_text())
    if not data.get("issue_id"):
        data["issue_id"] = issue_id
        summary_file.write_text(json.dumps(data, indent=2))


def event_already_summarized(event_id: str) -> bool:
    summary_file = DATA_DIR / event_id / "summary.json"
    if not summary_file.exists():
        return False
    data = json.loads(summary_file.read_text())
    return bool(data.get("summary"))


def load_all_summaries() -> list[dict]:
    """Return every saved summary.json, sorted newest first."""
    results = []
    for path in sorted(DATA_DIR.glob("*/summary.json"), reverse=True):
        try:
            results.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            pass
    return results


def load_raw_attachment(relative_path: str) -> bytes:
    return (DATA_DIR.parent.parent / relative_path).read_bytes()
