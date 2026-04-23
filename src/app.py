"""Main index page: one-line summary of every captured Sentry issue."""

import re

import streamlit as st

from src import theme
from src.storage import load_all_summaries

st.set_page_config(
    page_title="Sentry Error Attachment Summarizer",
    layout="wide",
    initial_sidebar_state="collapsed",
)
theme.apply()

summaries = load_all_summaries()

st.title("Sentry Error Attachment Summarizer")
st.caption("[:material/code: source](https://github.com/bengineerdavis/hackathon-support-spring-2026)")

if not summaries:
    st.info(
        "No summaries found. Run the pipeline first:\n\n"
        "```bash\nmise run pipeline\n```"
    )
    st.stop()

st.caption(
    f"{len(summaries)} error event(s) — each summarized from its raw attachments. "
    "Click any issue to view the AI analysis and research."
)

st.divider()


def _first_sentence(text: str) -> str:
    # Extract the "What happened:" line if present (structured AI output)
    m = re.search(r"\*\*What happened:\*\*\s*(.+?)(?:\n|$)", text)
    if m:
        return m.group(1).strip()
    m = re.match(r"[^.!?]*[.!?]", text.strip())
    return m.group(0).strip() if m else text[:150].rstrip() + "…"


for s in summaries:
    col_summary, col_meta, col_link = st.columns([5, 2, 1], vertical_alignment="center")

    with col_summary:
        st.markdown(f"#### `{s['title'] or s['event_id']}`")
        st.markdown(_first_sentence(s.get("summary", "_No summary available._")))

    with col_meta:
        n_att = len(s.get("attachments", []))
        st.caption(s["timestamp"][:10])
        st.caption(f"{n_att} attachment{'s' if n_att != 1 else ''}")

    with col_link:
        st.page_link(
            "pages/issue.py",
            label="View issue →",
            query_params={"event_id": s["event_id"]},
            use_container_width=True,
        )

    st.divider()
