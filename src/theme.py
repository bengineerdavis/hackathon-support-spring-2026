"""Sentry S.C.R.A.P.S.-inspired theme injected into every Streamlit page.

Palette reference:
  Purple (primary)  #6C5FC7
  Pink (accent)     #E56DB1
  Light purple      #AC93E6
  Muted             #9585A3
  Surface           #2B1D38  (set via config.toml secondaryBackgroundColor)
  Surface raised    #3A2D4A
  Border            #3A2F47
  Text              #EBE6EF  (set via config.toml textColor)
"""

import streamlit as st

_CSS = """
<style>
/* ── Fonts ─────────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600&family=Roboto+Mono:wght@400;500&display=swap');

html, body, [class*="css"], [data-testid="stSidebar"] {
    font-family: 'Rubik', sans-serif !important;
}

/* ── Tokens ─────────────────────────────────────────────────────────────────── */
:root {
    --s-purple:   #6C5FC7;
    --s-pink:     #E56DB1;
    --s-accent:   #AC93E6;
    --s-muted:    #9585A3;
    --s-surface2: #3A2D4A;
    --s-border:   #3A2F47;
    --s-gradient: linear-gradient(135deg, #6C5FC7 0%, #E56DB1 100%);
}

/* ── Page title: gradient text ──────────────────────────────────────────────── */
h1 {
    background: var(--s-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 600 !important;
    letter-spacing: -0.3px;
}

/* ── Issue title code block (### `ErrorType: ...`) ──────────────────────────── */
h3 code {
    font-family: 'Roboto Mono', monospace !important;
    color: var(--s-pink) !important;
    background-color: rgba(229, 109, 177, 0.12) !important;
    border-left: 3px solid var(--s-pink) !important;
    border-radius: 0 6px 6px 0 !important;
    padding: 0.2em 0.7em !important;
    font-size: 0.92em !important;
}

/* ── Inline code (everywhere else) ─────────────────────────────────────────── */
code {
    font-family: 'Roboto Mono', monospace !important;
    background-color: var(--s-surface2) !important;
    color: var(--s-accent) !important;
    border-radius: 4px !important;
    padding: 0.15em 0.45em !important;
    font-size: 0.87em !important;
}

/* ── Block code / log viewer ────────────────────────────────────────────────── */
[data-testid="stCode"] > div {
    background-color: var(--s-surface2) !important;
    border: 1px solid var(--s-border) !important;
    border-radius: 8px !important;
}

/* ── Primary link button: purple → pink gradient ────────────────────────────── */
[data-testid="stLinkButton"] a {
    font-family: 'Rubik', sans-serif !important;
    font-weight: 500 !important;
}

[data-testid="stLinkButton"] a[kind="primary"] {
    background: var(--s-gradient) !important;
    border: none !important;
    color: #fff !important;
}

[data-testid="stLinkButton"] a[kind="primary"]:hover {
    opacity: 0.88;
    box-shadow: 0 0 0 2px rgba(108, 95, 199, 0.45) !important;
}

/* ── Secondary / research button ───────────────────────────────────────────── */
.stButton > button {
    font-family: 'Rubik', sans-serif !important;
    border: 1px solid var(--s-border) !important;
    color: var(--s-accent) !important;
    background-color: var(--s-surface2) !important;
}

.stButton > button:hover {
    border-color: var(--s-purple) !important;
    background-color: rgba(108, 95, 199, 0.15) !important;
    color: #fff !important;
}

/* ── Page links (← All issues, View issue →) ────────────────────────────────── */
[data-testid="stPageLink"] a {
    font-family: 'Rubik', sans-serif !important;
    color: var(--s-accent) !important;
    border: 1px solid var(--s-border) !important;
    border-radius: 6px !important;
    transition: border-color 0.15s, background 0.15s;
}

[data-testid="stPageLink"] a:hover {
    border-color: var(--s-purple) !important;
    background: rgba(108, 95, 199, 0.12) !important;
    color: #fff !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--s-border) !important;
}

[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    background: transparent !important;
    border: none !important;
    color: var(--s-muted) !important;
    padding-left: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    color: var(--s-accent) !important;
    background: transparent !important;
}

/* ── Expanders ──────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--s-border) !important;
    border-radius: 8px !important;
    overflow: hidden;
}

[data-testid="stExpander"] summary p {
    font-weight: 500 !important;
    color: var(--s-accent) !important;
}

/* ── Dividers ───────────────────────────────────────────────────────────────── */
hr {
    border-color: var(--s-border) !important;
    opacity: 1 !important;
}

/* ── Captions / muted text ──────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p {
    color: var(--s-muted) !important;
}

/* ── Content width + centering ──────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] {
    max-width: 1000px !important;
    padding-top: 2.5rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* ── Column rows: vertically centered, even gap ──────────────────────────────── */
[data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: 1.25rem !important;
}

/* ── Button column min-width (prevents squash when sidebar widens) ──────────── */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
    min-width: 180px;
    flex-shrink: 0;
}

/* ── h4 code (main-page issue list titles) ──────────────────────────────────── */
h4 code {
    font-family: 'Roboto Mono', monospace !important;
    color: var(--s-pink) !important;
    background-color: rgba(229, 109, 177, 0.1) !important;
    border-left: 3px solid var(--s-pink) !important;
    border-radius: 0 4px 4px 0 !important;
    padding: 0.1em 0.55em !important;
    font-size: 0.82em !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────────── */
::-webkit-scrollbar            { width: 6px; height: 6px; }
::-webkit-scrollbar-track      { background: transparent; }
::-webkit-scrollbar-thumb      { background: var(--s-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--s-purple); }
</style>
"""


def apply() -> None:
    """Inject Sentry-branded styles. Call once per page, after set_page_config."""
    st.html(_CSS)
