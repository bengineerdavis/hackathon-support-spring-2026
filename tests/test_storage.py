"""Tests for the filesystem storage layer."""

import json
import pytest


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "x")
    monkeypatch.setenv("SENTRY_ORG_SLUG", "org")
    monkeypatch.setenv("SENTRY_PROJECT_SLUG", "proj")
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    """Return the storage module with DATA_DIR redirected to a temp dir."""
    import importlib
    import src.config as cfg
    importlib.reload(cfg)

    data_dir = tmp_path / "data" / "events"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr("src.config.DATA_DIR", data_dir)

    import src.storage as st
    importlib.reload(st)
    return st, data_dir


def _attachments():
    return [
        {"attachment_id": "att-1", "filename": "app.log", "raw": b"ERROR crash\n"},
        {"attachment_id": "att-2", "filename": "worker.log", "raw": b"INFO started\n"},
    ]


# --- save_summary ---

def test_save_summary_creates_json(storage):
    st, _ = storage
    path = st.save_summary("ev1", "ZeroDivisionError", "2026-04-21T10:00:00Z", "App crashed.", _attachments(), issue_id="iss-99")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["event_id"] == "ev1"
    assert data["issue_id"] == "iss-99"
    assert data["title"] == "ZeroDivisionError"
    assert data["summary"] == "App crashed."
    assert len(data["attachments"]) == 2


def test_save_summary_issue_id_defaults_empty(storage):
    st, _ = storage
    path = st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    data = json.loads(path.read_text())
    assert data["issue_id"] == ""


def test_save_summary_no_per_attachment_summary(storage):
    st, _ = storage
    path = st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    data = json.loads(path.read_text())
    for att in data["attachments"]:
        assert "summary" not in att


def test_save_summary_writes_raw_bytes(storage):
    st, data_dir = storage
    st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    assert (data_dir / "ev1" / "attachments" / "app.log").read_bytes() == b"ERROR crash\n"
    assert (data_dir / "ev1" / "attachments" / "worker.log").read_bytes() == b"INFO started\n"


def test_save_summary_attachment_records_have_raw_path(storage):
    st, _ = storage
    path = st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    data = json.loads(path.read_text())
    for att in data["attachments"]:
        assert "raw_path" in att
        assert att["filename"] in att["raw_path"]


# --- patch_issue_id ---

def test_patch_issue_id_writes_missing_id(storage):
    st, data_dir = storage
    path = st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    st.patch_issue_id("ev1", "iss-42")
    data = json.loads(path.read_text())
    assert data["issue_id"] == "iss-42"


def test_patch_issue_id_does_not_overwrite_existing(storage):
    st, _ = storage
    path = st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments(), issue_id="iss-original")
    st.patch_issue_id("ev1", "iss-new")
    data = json.loads(path.read_text())
    assert data["issue_id"] == "iss-original"


def test_patch_issue_id_noop_when_no_file(storage):
    st, _ = storage
    st.patch_issue_id("nonexistent", "iss-42")  # should not raise


# --- event_already_summarized ---

def test_event_already_summarized_false_when_no_file(storage):
    st, _ = storage
    assert st.event_already_summarized("nonexistent") is False


def test_event_already_summarized_true_after_save(storage):
    st, _ = storage
    st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    assert st.event_already_summarized("ev1") is True


def test_event_already_summarized_false_for_empty_summary(storage):
    st, data_dir = storage
    event_dir = data_dir / "ev1"
    event_dir.mkdir()
    (event_dir / "summary.json").write_text(json.dumps({"event_id": "ev1", "summary": ""}))
    assert st.event_already_summarized("ev1") is False


# --- load_all_summaries ---

def test_load_all_summaries_returns_saved(storage):
    st, _ = storage
    st.save_summary("ev1", "Error A", "2026-04-21T10:00:00Z", "Summary A.", _attachments())
    st.save_summary("ev2", "Error B", "2026-04-21T11:00:00Z", "Summary B.", _attachments())
    results = st.load_all_summaries()
    ids = {r["event_id"] for r in results}
    assert ids == {"ev1", "ev2"}


def test_load_all_summaries_empty_when_no_data(storage):
    st, _ = storage
    assert st.load_all_summaries() == []


def test_load_all_summaries_skips_malformed_json(storage):
    st, data_dir = storage
    st.save_summary("ev1", "Good", "2026-04-21T10:00:00Z", "Summary.", _attachments())
    bad_dir = data_dir / "ev-bad"
    bad_dir.mkdir()
    (bad_dir / "summary.json").write_text("{not valid json")
    results = st.load_all_summaries()
    assert len(results) == 1
    assert results[0]["event_id"] == "ev1"


# --- load_raw_attachment ---

def test_load_raw_attachment_returns_bytes(storage):
    st, _ = storage
    st.save_summary("ev1", "err", "2026-04-21T00:00:00Z", "Summary.", _attachments())
    import src.storage as storage_module
    import importlib
    importlib.reload(storage_module)
    # Use the fixture's reloaded module which has the patched DATA_DIR
    raw = st.load_raw_attachment("data/events/ev1/attachments/app.log")
    assert raw == b"ERROR crash\n"


def test_load_raw_attachment_raises_on_missing(storage):
    st, _ = storage
    with pytest.raises(FileNotFoundError):
        st.load_raw_attachment("data/events/nonexistent/attachments/nope.log")
