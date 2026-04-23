"""Tests for the LLM summarization layer."""

import pytest
from unittest.mock import MagicMock, patch


ATTACHMENTS = [
    ("app.log", "2026-04-21 ERROR ZeroDivisionError: division by zero\n"),
    ("worker.log", "2026-04-21 INFO worker started\n2026-04-21 ERROR crash\n"),
]


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "x")
    monkeypatch.setenv("SENTRY_ORG_SLUG", "org")
    monkeypatch.setenv("SENTRY_PROJECT_SLUG", "proj")
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monkeypatch.setenv("LLM_MODEL", "ollama/llama3")


def _make_mock_model(response_text: str):
    mock_response = MagicMock()
    mock_response.text.return_value = response_text
    mock_model = MagicMock()
    mock_model.prompt.return_value = mock_response
    return mock_model


def test_summarize_returns_text():
    mock_model = _make_mock_model("The app crashed due to a division by zero.")

    with patch("llm.get_model", return_value=mock_model):
        from src.summarizer import summarize
        result = summarize(ATTACHMENTS, title="ZeroDivisionError")

    assert result == "The app crashed due to a division by zero."


def test_summarize_includes_title_in_prompt():
    mock_model = _make_mock_model("Summary.")

    with patch("llm.get_model", return_value=mock_model):
        from src.summarizer import summarize
        summarize(ATTACHMENTS, title="MyError")

    prompt_text = mock_model.prompt.call_args[0][0]
    assert "MyError" in prompt_text


def test_summarize_includes_all_filenames_in_prompt():
    mock_model = _make_mock_model("Summary.")

    with patch("llm.get_model", return_value=mock_model):
        from src.summarizer import summarize
        summarize(ATTACHMENTS, title="err")

    prompt_text = mock_model.prompt.call_args[0][0]
    assert "app.log" in prompt_text
    assert "worker.log" in prompt_text


def test_summarize_includes_attachment_count():
    mock_model = _make_mock_model("Summary.")

    with patch("llm.get_model", return_value=mock_model):
        from src.summarizer import summarize
        summarize(ATTACHMENTS, title="err")

    prompt_text = mock_model.prompt.call_args[0][0]
    assert "2" in prompt_text


def test_summarize_truncates_large_attachment():
    huge = [("big.log", "x" * 20_000)]
    mock_model = _make_mock_model("Summary.")

    with patch("llm.get_model", return_value=mock_model):
        from src.summarizer import summarize
        summarize(huge)

    prompt_text = mock_model.prompt.call_args[0][0]
    assert len(prompt_text) < 15_000


def test_summarize_uses_configured_model(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "ollama/mistral")
    import importlib
    import src.config as cfg
    importlib.reload(cfg)

    mock_model = _make_mock_model("ok")
    with patch("llm.get_model", return_value=mock_model) as mock_get:
        import src.summarizer as sm
        importlib.reload(sm)
        sm.summarize(ATTACHMENTS)
        mock_get.assert_called_once_with("ollama/mistral")


# --- run_pipeline ---

@pytest.fixture()
def pipeline_mocks():
    """Return a dict of mocks for all run_pipeline dependencies."""
    with (
        patch("src.sentry_client.assert_permissions") as mock_assert,
        patch("src.sentry_client.iter_all_issues") as mock_issues,
        patch("src.sentry_client.get_latest_event") as mock_event,
        patch("src.sentry_client.list_attachments") as mock_attachments,
        patch("src.sentry_client.download_attachment") as mock_download,
        patch("src.storage.save_summary") as mock_save,
        patch("src.storage.event_already_summarized") as mock_summarized,
        patch("src.storage.patch_issue_id") as mock_patch,
        patch("llm.get_model") as mock_get_model,
    ):
        mock_get_model.return_value = _make_mock_model("Test summary.")
        yield {
            "assert_permissions": mock_assert,
            "iter_all_issues": mock_issues,
            "get_latest_event": mock_event,
            "list_attachments": mock_attachments,
            "download_attachment": mock_download,
            "save_summary": mock_save,
            "event_already_summarized": mock_summarized,
            "patch_issue_id": mock_patch,
        }


def test_run_pipeline_happy_path(pipeline_mocks):
    m = pipeline_mocks
    m["iter_all_issues"].return_value = [{"id": "iss-1", "title": "ZeroDivisionError"}]
    m["get_latest_event"].return_value = {"id": "ev-1", "dateCreated": "2026-04-21T10:00:00Z"}
    m["event_already_summarized"].return_value = False
    m["list_attachments"].return_value = [{"id": "1", "name": "app.log"}]
    m["download_attachment"].return_value = b"ERROR crash\n"

    from src.summarizer import run_pipeline
    run_pipeline()

    m["save_summary"].assert_called_once()
    call_kwargs = m["save_summary"].call_args
    assert call_kwargs.kwargs.get("issue_id") == "iss-1" or call_kwargs.args[5] == "iss-1"


def test_run_pipeline_calls_patch_issue_id_on_skip(pipeline_mocks):
    m = pipeline_mocks
    m["iter_all_issues"].return_value = [{"id": "iss-1", "title": "ZeroDivisionError"}]
    m["get_latest_event"].return_value = {"id": "ev-1", "dateCreated": "2026-04-21T10:00:00Z"}
    m["event_already_summarized"].return_value = True

    from src.summarizer import run_pipeline
    run_pipeline()

    m["patch_issue_id"].assert_called_once_with("ev-1", "iss-1")
    m["save_summary"].assert_not_called()


def test_run_pipeline_skips_events_without_attachments(pipeline_mocks):
    m = pipeline_mocks
    m["iter_all_issues"].return_value = [{"id": "iss-1", "title": "ZeroDivisionError"}]
    m["get_latest_event"].return_value = {"id": "ev-1", "dateCreated": "2026-04-21T10:00:00Z"}
    m["event_already_summarized"].return_value = False
    m["list_attachments"].return_value = []

    from src.summarizer import run_pipeline
    run_pipeline()

    m["save_summary"].assert_not_called()
