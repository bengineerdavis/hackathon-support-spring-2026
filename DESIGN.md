# Design

## Design language: S.C.R.A.P.S.

This tool is styled to look and feel like an internal Sentry service, following Sentry's **S.C.R.A.P.S.** design language — *Standardized Collection of Reusable Assets and Patterns for Sentry*.

S.C.R.A.P.S. describes a dark-themed, data-dense interface with pink-purple accents, monospace clarity for technical content, and a bold brand personality. The goals for this tool specifically:

- A developer scanning crash logs should immediately recognize the interface as part of the Sentry ecosystem.
- Error strings and code identifiers should be visually distinct from prose — not buried in plain text.
- Navigation between an issue index and individual issue pages should feel lightweight and consistent.

---

## Color palette

| Token | Hex | Role |
| --- | --- | --- |
| `--s-purple` | `#6C5FC7` | Primary brand color — buttons, active states, focus rings |
| `--s-pink` | `#E56DB1` | Secondary accent — issue title highlights, gradient endpoint |
| `--s-accent` | `#AC93E6` | Light purple — links, expander headers, inline code |
| `--s-muted` | `#9585A3` | Subdued purple-grey — captions, sidebar secondary text |
| `--s-surface2` | `#3A2D4A` | Raised surface — code blocks, secondary buttons |
| `--s-border` | `#3A2F47` | Borders and dividers |
| Background | `#1A1A1A` | Page background (set in `config.toml`) |
| Surface | `#2B1D38` | Sidebar and card backgrounds (set in `config.toml`) |
| Text | `#EBE6EF` | Primary text (set in `config.toml`) |

The **gradient** (`135deg, #6C5FC7 → #E56DB1`) is used on primary call-to-action buttons and the page `h1` title — the same purple-to-pink sweep seen in Sentry's marketing and product brand assets.

**Sources:**
- Sentry brand/press kit at [sentry.io/branding](https://sentry.io/branding/)
- Sentry's open-source frontend repo (`getsentry/sentry`) — `src/sentry/static/sentry/app/utils/theme.tsx` and the `@sentry/design-system` package contain the canonical token values
- Google AI overview of S.C.R.A.P.S.: *"dark-themed, data-dense interface utilizing pink-purple accents … bold, illustrative brand personality featuring characters and vibrant gradients"*

---

## Typography

| Use | Typeface | Weight |
| --- | --- | --- |
| UI text, headings, labels | [Rubik](https://fonts.google.com/specimen/Rubik) | 400 / 500 / 600 |
| Code, log output, identifiers | [Roboto Mono](https://fonts.google.com/specimen/Roboto+Mono) | 400 / 500 |

Rubik is Sentry's primary product UI font. Roboto Mono is used for anything that maps to code — error type strings, event IDs, log files, and inline `code` spans. Both are loaded from Google Fonts.

---

## Visual treatment by element

### Page title (`h1`)
Rendered with the purple → pink gradient using `background-clip: text`. This is the same technique Sentry uses on feature landing pages and in some dashboard headers.

### Issue title (`h3 code`)
Error names like `` `TypeError: unsupported operand type(s) for /: 'str' and 'int'` `` are wrapped in a pink translucent block with a left-side pink border. This mimics the way Sentry's issue detail page visually separates the error class from the surrounding prose — a terminal-style callout that signals "this is the thing that broke."

### Inline code
Uses `--s-accent` (light purple) on a raised surface background — consistent with how Sentry's UI renders identifiers like event IDs and SDK names in running text.

### Primary button (Sentry link)
The "Open issue in Sentry" and "View trace in Sentry" buttons carry the gradient fill so they have the weight of a primary brand action, not just a utility link.

### Secondary button (Research)
Bordered, dark-surface style — visually subordinate to the Sentry link but still clearly interactive. Border turns purple on hover to echo the primary palette.

### Expanders (Research sections)
Bordered with `--s-border`, headers in `--s-accent`. Each section (Help Center, Docs, Web, Similar sessions) is visually contained without being heavy — consistent with Sentry's "panels within a panel" layout style.

### Scrollbar
Thin (`6px`), thumb in `--s-border`, turns `--s-purple` on hover. Matches the minimal scrollbar treatment seen in Sentry's desktop app.

---

## Implementation

All styles live in [`src/theme.py`](src/theme.py) as a single injected `<style>` block. The Streamlit base theme (`[theme]` in [`.streamlit/config.toml`](.streamlit/config.toml)) sets the four foundational values — background, surface, primary, and text — so that Streamlit's own widgets (radios, selectboxes, spinners) automatically follow the palette. The CSS in `theme.py` handles everything the base theme cannot: gradients, custom fonts, component-specific overrides, and the issue title treatment.

Both pages call `theme.apply()` immediately after `st.set_page_config()`.

```
.streamlit/config.toml   base palette (backgroundColor, primaryColor, textColor, …)
src/theme.py             fonts, gradients, per-component CSS overrides
src/app.py               theme.apply()
src/pages/issue.py       theme.apply()
```
