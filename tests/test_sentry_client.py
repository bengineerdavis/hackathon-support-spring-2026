"""Tests for the Sentry REST API client."""

import pytest
import responses as rsps_lib

import src.sentry_client as client

BASE_PROJ = "https://sentry.io/api/0/projects/my-org/my-project"
BASE_ORG = "https://sentry.io/api/0/organizations/my-org"


def _patch_env(monkeypatch):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("SENTRY_ORG_SLUG", "my-org")
    monkeypatch.setenv("SENTRY_PROJECT_SLUG", "my-project")
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monkeypatch.setenv("SENTRY_BASE_URL", "https://sentry.io")


@pytest.fixture(autouse=True)
def reload_config(monkeypatch):
    _patch_env(monkeypatch)
    import importlib, src.config as cfg
    importlib.reload(cfg)
    importlib.reload(client)


# --- list_issues ---

@rsps_lib.activate
def test_list_issues_returns_data():
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_PROJ}/issues/",
        json=[{"id": "123", "title": "ZeroDivisionError"}],
        status=200,
    )
    result = client.list_issues()
    assert result["data"] == [{"id": "123", "title": "ZeroDivisionError"}]


@rsps_lib.activate
def test_list_issues_sends_auth_header():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[], status=200)
    client.list_issues()
    assert rsps_lib.calls[0].request.headers["Authorization"] == "Bearer test-token"


@rsps_lib.activate
def test_iter_all_issues_follows_pagination():
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_PROJ}/issues/",
        json=[{"id": "iss1"}],
        status=200,
        headers={
            "Link": f'<{BASE_PROJ}/issues/?cursor=1:0:0>; rel="next"; results="true"; cursor=1:0:0'
        },
    )
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_PROJ}/issues/",
        json=[{"id": "iss2"}],
        status=200,
        headers={"Link": ""},
    )
    issues = client.iter_all_issues()
    assert [i["id"] for i in issues] == ["iss1", "iss2"]


# --- get_latest_event ---

@rsps_lib.activate
def test_get_latest_event_returns_event():
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_ORG}/issues/123/events/latest/",
        json={"id": "ev-abc", "dateCreated": "2026-04-21T10:00:00Z"},
        status=200,
    )
    result = client.get_latest_event("123")
    assert result["id"] == "ev-abc"


@rsps_lib.activate
def test_get_latest_event_sends_auth_header():
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_ORG}/issues/123/events/latest/",
        json={"id": "ev-abc"},
        status=200,
    )
    client.get_latest_event("123")
    assert rsps_lib.calls[0].request.headers["Authorization"] == "Bearer test-token"


# --- list_attachments / download_attachment ---

@rsps_lib.activate
def test_list_attachments():
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_PROJ}/events/ev-abc/attachments/",
        json=[{"id": "1", "name": "app.log"}],
        status=200,
    )
    result = client.list_attachments("ev-abc")
    assert result == [{"id": "1", "name": "app.log"}]


@rsps_lib.activate
def test_download_attachment():
    raw = b"2026-04-21 ERROR crash\n"
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_PROJ}/events/ev-abc/attachments/1/",
        body=raw,
        status=200,
    )
    result = client.download_attachment("ev-abc", "1")
    assert result == raw
    assert rsps_lib.calls[0].request.params["download"] == "1"


# --- check_permissions / assert_permissions ---

@rsps_lib.activate
def test_check_permissions_all_granted():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[], status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/0/events/latest/", json={}, status=404)
    result = client.check_permissions()
    assert result == {"project:read": True, "event:read": True}


@rsps_lib.activate
def test_check_permissions_both_missing():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json={}, status=403)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/0/events/latest/", json={}, status=403)
    result = client.check_permissions()
    assert result == {"project:read": False, "event:read": False}


@rsps_lib.activate
def test_check_permissions_partial():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[], status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/0/events/latest/", json={}, status=403)
    result = client.check_permissions()
    assert result["project:read"] is True
    assert result["event:read"] is False


@rsps_lib.activate
def test_assert_permissions_raises_on_missing(capsys):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json={}, status=403)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/0/events/latest/", json={}, status=403)
    with pytest.raises(PermissionError, match="Missing scopes"):
        client.assert_permissions()


@rsps_lib.activate
def test_assert_permissions_passes_when_all_granted(capsys):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[], status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/0/events/latest/", json={}, status=404)
    client.assert_permissions()  # should not raise
    out = capsys.readouterr().out
    assert "✓ project:read" in out
    assert "✓ event:read" in out


@rsps_lib.activate
def test_raise_for_status_403_mentions_scope():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json={}, status=403)
    with pytest.raises(PermissionError, match="project:read"):
        client.list_issues()


@rsps_lib.activate
def test_raise_for_status_non_403_raises_http_error():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json={}, status=500)
    import requests
    with pytest.raises(requests.exceptions.HTTPError):
        client.list_issues()


@rsps_lib.activate
def test_list_issues_passes_cursor_param():
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[], status=200)
    client.list_issues(cursor="1:0:0")
    assert rsps_lib.calls[0].request.params["cursor"] == "1:0:0"


# --- caching behaviour ---

@rsps_lib.activate
def test_iter_all_issues_caches_result(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[{"id": "iss1"}], status=200)
    first = client.iter_all_issues()
    second = client.iter_all_issues()
    assert first == second == [{"id": "iss1"}]
    assert len(rsps_lib.calls) == 1  # only one real HTTP call


@rsps_lib.activate
def test_iter_all_issues_force_refresh_bypasses_cache(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[{"id": "iss1"}], status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/issues/", json=[{"id": "iss2"}], status=200)
    client.iter_all_issues()
    result = client.iter_all_issues(force_refresh=True)
    assert result == [{"id": "iss2"}]
    assert len(rsps_lib.calls) == 2


@rsps_lib.activate
def test_get_latest_event_caches_result(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/123/events/latest/", json={"id": "ev1"}, status=200)
    first = client.get_latest_event("123")
    second = client.get_latest_event("123")
    assert first == second == {"id": "ev1"}
    assert len(rsps_lib.calls) == 1


@rsps_lib.activate
def test_get_latest_event_force_refresh(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/123/events/latest/", json={"id": "ev1"}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_ORG}/issues/123/events/latest/", json={"id": "ev2"}, status=200)
    client.get_latest_event("123")
    result = client.get_latest_event("123", force_refresh=True)
    assert result == {"id": "ev2"}


@rsps_lib.activate
def test_list_attachments_caches_result(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/events/ev-abc/attachments/", json=[{"id": "1"}], status=200)
    client.list_attachments("ev-abc")
    client.list_attachments("ev-abc")
    assert len(rsps_lib.calls) == 1


@rsps_lib.activate
def test_download_attachment_caches_result(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/events/ev-abc/attachments/1/", body=b"raw", status=200)
    client.download_attachment("ev-abc", "1")
    result = client.download_attachment("ev-abc", "1")
    assert result == b"raw"
    assert len(rsps_lib.calls) == 1


@rsps_lib.activate
def test_download_attachment_force_refresh(fresh_cache):
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/events/ev-abc/attachments/1/", body=b"old", status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE_PROJ}/events/ev-abc/attachments/1/", body=b"new", status=200)
    client.download_attachment("ev-abc", "1")
    result = client.download_attachment("ev-abc", "1", force_refresh=True)
    assert result == b"new"


# --- _parse_next_cursor ---

def test_parse_next_cursor_returns_none_when_no_next():
    link = '<https://sentry.io/api/0/projects/org/proj/issues/?cursor=0:0:1>; rel="previous"; results="false"; cursor=0:0:1'
    assert client._parse_next_cursor(link) is None


def test_parse_next_cursor_extracts_value():
    link = (
        '<https://sentry.io/api/0/projects/org/proj/issues/?cursor=1:0:0>; rel="next"; results="true"; cursor=1:0:0, '
        '<https://sentry.io/api/0/projects/org/proj/issues/?cursor=0:0:1>; rel="previous"; results="false"; cursor=0:0:1'
    )
    assert client._parse_next_cursor(link) == "1:0:0"
