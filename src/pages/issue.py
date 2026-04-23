"""Issue detail page: full summary, attachments, Sentry link, and research."""

import streamlit as st

from src import theme
from src.config import SENTRY_ORG_SLUG
from src.research import load_session, research_issue
from src.storage import load_all_summaries, load_raw_attachment

st.set_page_config(
    page_title="Issue — Sentry Log Summarizer",
    layout="wide",
)
theme.apply()

# ── Load data ─────────────────────────────────────────────────────────────────

summaries = load_all_summaries()
event_id = st.query_params.get("event_id")
event = next((s for s in summaries if s["event_id"] == event_id), None)

# ── Sidebar: navigation ───────────────────────────────────────────────────────

with st.sidebar:
    st.page_link("app.py", label="← All issues", icon=":material/arrow_back:")
    st.divider()

    if summaries:
        st.caption("Switch issue")
        labels = [
            f"{s['title'][:45] or s['event_id']} — {s['timestamp'][:10]}"
            for s in summaries
        ]
        current_idx = next(
            (i for i, s in enumerate(summaries) if s["event_id"] == event_id), 0
        )
        selected_idx = st.radio(
            "switch_issue",
            range(len(summaries)),
            index=current_idx,
            format_func=lambda i: labels[i],
            label_visibility="collapsed",
        )
        if summaries[selected_idx]["event_id"] != event_id:
            st.query_params["event_id"] = summaries[selected_idx]["event_id"]
            st.rerun()

# ── Guard: no valid event_id ──────────────────────────────────────────────────

if event is None:
    st.warning("No issue selected or issue not found.")
    st.page_link("app.py", label="← Back to all issues")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────


def _primary_sentry_button(ev: dict) -> tuple[str, str, str] | None:
    issue_id = ev.get("issue_id")
    if not issue_id:
        return None
    trace_id = ev.get("trace_id")
    if trace_id:
        return (
            f"https://{SENTRY_ORG_SLUG}.sentry.io/performance/trace/{trace_id}/",
            "View trace in Sentry",
            ":material/timeline:",
        )
    return (
        f"https://{SENTRY_ORG_SLUG}.sentry.io/issues/{issue_id}",
        "Open issue in Sentry",
        ":material/open_in_new:",
    )


col_title, col_btn = st.columns([4, 1], vertical_alignment="center")
with col_title:
    st.markdown(f"### `{event['title'] or event['event_id']}`")
    st.caption(
        f"Event `{event['event_id']}` · "
        f"Issue `{event.get('issue_id', '—')}` · "
        f"{event['timestamp']} · "
        "[:material/code: source](https://github.com/bengineerdavis/hackathon-support-spring-2026)"
    )
with col_btn:
    btn = _primary_sentry_button(event)
    if btn:
        url, label, icon = btn
        st.link_button(label, url, icon=icon, type="primary", use_container_width=True)

# ── Summary ───────────────────────────────────────────────────────────────────

st.markdown("### AI Analysis")
st.caption("Generated from the raw log attachments below — not reproduced verbatim.")
st.markdown(event.get("summary", "_No summary available._"))

# ── Attachments ───────────────────────────────────────────────────────────────

attachments = event.get("attachments", [])
if attachments:
    st.markdown("### Attachments")
    st.caption(
        f"{len(attachments)} file{'s' if len(attachments) != 1 else ''} — "
        "all processed together as context for the summary above"
    )
    for att in attachments:
        with st.expander(att["filename"]):
            try:
                raw_text = load_raw_attachment(att["raw_path"]).decode(
                    "utf-8", errors="replace"
                )
                st.code(raw_text, language="text")
            except FileNotFoundError:
                st.error("Raw attachment file not found on disk.")

# ── Research ──────────────────────────────────────────────────────────────────

st.markdown("### Research")
session = load_session(event["event_id"])

if session is None:
    if st.button("Research this issue", icon=":material/search:", type="secondary"):
        with st.spinner("Searching Sentry Help Center, docs, and web…"):
            session = research_issue(
                event_id=event["event_id"],
                issue_id=event.get("issue_id", ""),
                title=event["title"],
                summary=event.get("summary", ""),
            )
        st.rerun()
    st.caption(
        "Searches the Sentry Help Center, sentry-docs (if indexed), and the web. "
        "Results are cached per issue."
    )

if session:
    help_results = session.get("help_results") or []
    with st.expander(f"Sentry Help Center ({len(help_results)} articles)", expanded=True):
        if help_results:
            for r in help_results:
                st.markdown(f"**[{r['title']}]({r['url']})**")
                st.caption(r.get("snippet", ""))
        else:
            st.caption("No help articles found for this query.")

    doc_results = session.get("doc_results") or []
    with st.expander(f"Sentry docs ({len(doc_results)} results)"):
        if doc_results:
            for r in doc_results:
                url = r.get("url")
                if url:
                    st.markdown(f"**[{r['source']}]({url})**")
                else:
                    st.markdown(f"**`{r['source']}`**")
                st.markdown(r["text"])
                st.divider()
        else:
            st.caption("No docs results — run `mise run index-docs` to build the index.")

    web_results = session.get("web_results") or []
    with st.expander(f"Web search ({len(web_results)} results)"):
        for r in web_results:
            if r.get("url"):
                st.markdown(f"**[{r['title']}]({r['url']})**")
            else:
                st.markdown(f"**{r['title']}**")
            st.caption(r.get("snippet", ""))

    similar = session.get("similar_sessions") or []
    if similar:
        with st.expander(f"Similar past sessions ({len(similar)})"):
            for s in similar:
                st.markdown(f"- `{s['title'][:80]}` — event `{s['event_id'][:12]}…`")

# ── Footer nav ────────────────────────────────────────────────────────────────

st.divider()
st.page_link("app.py", label="← Back to all issues", icon=":material/arrow_back:")
