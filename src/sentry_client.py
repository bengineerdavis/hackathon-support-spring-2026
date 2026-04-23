"""Thin wrapper around the Sentry REST API for issues, events, and attachments."""

import requests
from typing import Any
from src.config import SENTRY_AUTH_TOKEN, SENTRY_BASE_URL, SENTRY_ORG_SLUG, SENTRY_PROJECT_SLUG

_REQUIRED_SCOPES: dict[str, str] = {
    "project:read": "list issues in the project",
    "event:read": "fetch events and download attachments",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"})
    return s


def _api(path: str) -> str:
    return f"{SENTRY_BASE_URL}/api/0{path}"


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

def check_permissions() -> dict[str, bool]:
    """Probe each required API scope. Returns {scope: has_access}.

    Uses innocuous requests — a 404 response means the token has access but the
    resource doesn't exist, which is fine. A 403 means the scope is missing.
    """
    results: dict[str, bool] = {}

    try:
        resp = _session().get(
            _api(f"/projects/{SENTRY_ORG_SLUG}/{SENTRY_PROJECT_SLUG}/issues/"),
            params={"limit": "1"},
            timeout=10,
        )
        results["project:read"] = resp.status_code != 403
    except requests.exceptions.RequestException:
        results["project:read"] = False

    try:
        resp = _session().get(
            _api(f"/organizations/{SENTRY_ORG_SLUG}/issues/0/events/latest/"),
            timeout=10,
        )
        results["event:read"] = resp.status_code != 403
    except requests.exceptions.RequestException:
        results["event:read"] = False

    return results


def assert_permissions() -> None:
    """Check required scopes and raise a descriptive error if any are missing."""
    results = check_permissions()
    missing = [scope for scope, ok in results.items() if not ok]

    lines = ["Sentry API token permissions:"]
    for scope, ok in results.items():
        mark = "✓" if ok else "✗"
        lines.append(f"  {mark} {scope}  — {_REQUIRED_SCOPES[scope]}")
    print("\n".join(lines))

    if missing:
        raise PermissionError(
            "\nMissing scopes: " + ", ".join(missing) +
            "\n→ sentry.io → Settings → Auth Tokens → edit your token and add the missing scopes."
        )


# ---------------------------------------------------------------------------
# Issues  (cached, TTL_ISSUES)
# ---------------------------------------------------------------------------

def list_issues(cursor: str | None = None) -> dict[str, Any]:
    """Return one page of issues (uncached). Requires project:read."""
    params: dict[str, str] = {"limit": "100"}
    if cursor:
        params["cursor"] = cursor
    resp = _session().get(
        _api(f"/projects/{SENTRY_ORG_SLUG}/{SENTRY_PROJECT_SLUG}/issues/"),
        params=params,
        timeout=15,
    )
    _raise_for_status(resp, scope="project:read", endpoint="list issues")
    return {"data": resp.json(), "headers": dict(resp.headers)}


def iter_all_issues(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return all issues, served from cache unless stale or force_refresh=True."""
    from src.cache import cache, TTL_ISSUES
    key = f"issues|{SENTRY_ORG_SLUG}|{SENTRY_PROJECT_SLUG}"
    if not force_refresh:
        hit = cache.get(key)
        if hit is not None:
            return hit
    issues: list[dict[str, Any]] = []
    cursor = None
    while True:
        page = list_issues(cursor=cursor)
        issues.extend(page["data"])
        next_cursor = _parse_next_cursor(page["headers"].get("Link", ""))
        if not next_cursor:
            break
        cursor = next_cursor
    cache.set(key, issues, expire=TTL_ISSUES)
    return issues


# ---------------------------------------------------------------------------
# Events  (cached, TTL_EVENT)
# ---------------------------------------------------------------------------

def get_latest_event(issue_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Return the latest event for an issue. Requires event:read."""
    from src.cache import cache, TTL_EVENT
    key = f"event|{SENTRY_ORG_SLUG}|{issue_id}"
    if not force_refresh:
        hit = cache.get(key)
        if hit is not None:
            return hit
    resp = _session().get(
        _api(f"/organizations/{SENTRY_ORG_SLUG}/issues/{issue_id}/events/latest/"),
        timeout=15,
    )
    _raise_for_status(resp, scope="event:read", endpoint="get latest event")
    result = resp.json()
    cache.set(key, result, expire=TTL_EVENT)
    return result


# ---------------------------------------------------------------------------
# Attachments  (cached, TTL_ATTACHMENT)
# ---------------------------------------------------------------------------

def list_attachments(event_id: str, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return attachment metadata for an event. Requires event:read."""
    from src.cache import cache, TTL_ATTACHMENT
    key = f"attachments|{SENTRY_ORG_SLUG}|{event_id}"
    if not force_refresh:
        hit = cache.get(key)
        if hit is not None:
            return hit
    resp = _session().get(
        _api(f"/projects/{SENTRY_ORG_SLUG}/{SENTRY_PROJECT_SLUG}/events/{event_id}/attachments/"),
        timeout=15,
    )
    _raise_for_status(resp, scope="event:read", endpoint="list attachments")
    result = resp.json()
    cache.set(key, result, expire=TTL_ATTACHMENT)
    return result


def download_attachment(
    event_id: str,
    attachment_id: str,
    force_refresh: bool = False,
) -> bytes:
    """Download raw attachment bytes. Requires event:read."""
    from src.cache import cache, TTL_ATTACHMENT
    key = f"attachment_bytes|{SENTRY_ORG_SLUG}|{event_id}|{attachment_id}"
    if not force_refresh:
        hit = cache.get(key)
        if hit is not None:
            return hit
    resp = _session().get(
        _api(
            f"/projects/{SENTRY_ORG_SLUG}/{SENTRY_PROJECT_SLUG}"
            f"/events/{event_id}/attachments/{attachment_id}/"
        ),
        params={"download": "1"},
        timeout=30,
    )
    _raise_for_status(resp, scope="event:read", endpoint="download attachment")
    result = resp.content
    cache.set(key, result, expire=TTL_ATTACHMENT)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_next_cursor(link_header: str) -> str | None:
    for part in link_header.split(","):
        if 'rel="next"' in part and 'results="true"' in part:
            for segment in part.split(";"):
                segment = segment.strip()
                if segment.startswith("cursor="):
                    return segment[len("cursor="):]
    return None


def _raise_for_status(resp: requests.Response, scope: str, endpoint: str) -> None:
    if resp.status_code == 403:
        raise PermissionError(
            f"403 Forbidden calling '{endpoint}'.\n"
            f"  Missing scope: {scope}  — {_REQUIRED_SCOPES.get(scope, '')}\n"
            f"  → sentry.io → Settings → Auth Tokens → add '{scope}' to your token.\n"
            f"  Run 'mise run check-access' for a full permissions report."
        )
    resp.raise_for_status()


if __name__ == "__main__":
    issues = iter_all_issues()
    print(f"Found {len(issues)} issues")
    for issue in issues[:5]:
        print(f"  {issue['id']}  {issue.get('title', '(no title)')}")
