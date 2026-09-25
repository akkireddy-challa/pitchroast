"""PitchRoast — a satirical AI venture committee that roasts your startup pitch.

This file is the router and nothing else. It owns the page shell, the shared
session state, and the switch between the two entry points:

    ?mode=founder  →  founder.py   the founder-facing hot seat (default)
    ?mode=admin    →  admin.py     the judge-facing command centre

Both views read and write the same session state, so a verdict convened in one
is still there after the toggle — flipping modes never costs an API call. The
split exists because the two audiences want opposite things: a founder wants a
boardroom, and a judge wants the instruments.

    app.py        router, page shell, mode switch
    founder.py    the Founder Hot Seat
    admin.py      the Syndicate Observatory
    board.py      verdict rendering + the live run, shared by both
    state.py      session state, operator settings, Phoenix bootstrap
    costs.py      token → credit arithmetic
    syndicate.py  every Anthropic call in the project

All model orchestration lives in `syndicate.py`. Model-produced text is never
rendered as HTML anywhere in the UI.
"""

from __future__ import annotations

import logging

import streamlit as st
from dotenv import load_dotenv

import admin
import founder
import state
from ui import inject_flair

logger = logging.getLogger(__name__)

load_dotenv()

st.set_page_config(
    page_title="PitchRoast — autonomous VC syndicate",
    page_icon=":material/local_fire_department:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Motion only (keyframes scoped to .st-key-* classes). Colour, fonts and radii
# stay in .streamlit/config.toml; this decorates the native containers rather
# than replacing them. Implements the interactions named in SPEC.md §2.
inject_flair()

state.init()

# Start Phoenix before either view draws. Tracing has to run in founder mode
# too — the founder never sees it, but their roast is exactly what the judges
# come to the Observatory to inspect. Cached, so this is a no-op after the
# first script run in the process.
state.tracing()


# --------------------------------------------------------------------------
# Mode switch
# --------------------------------------------------------------------------
# Opening ?mode=admin selects the Observatory; clicking a segment rewrites the
# URL, so either view is a link you can hand to someone. An unrecognised value
# falls back to the founder view instead of raising.
#
# Synced by hand rather than with `bind="query-params"` — the one place in this
# app where that is the right call. Option widgets put the *formatted* label on
# the wire, so `bind` plus a format_func writes `?mode=🔬 Syndicate observatory`
# into the URL. The contract here is `?mode=founder` / `?mode=admin`, which
# means the URL value and the button label have to differ. `state.init()` seeds
# session state from the URL before this renders, and the on_change callback
# writes it back before the rerun draws — so there is no extra rerun and no
# "modified after widget creation" exception.
#
# This is a UX boundary, not an authorisation one: anyone can type ?mode=admin,
# and the Observatory deliberately shows only local, non-secret operational data.

with st.container(horizontal=True, horizontal_alignment="right"):
    st.segmented_control(
        "View",
        options=list(state.MODE_LABELS),
        required=True,
        format_func=lambda value: state.MODE_LABELS[value],
        key=state.K_MODE,
        on_change=state.sync_mode_to_url,
        label_visibility="collapsed",
    )

if state.mode() == state.ADMIN:
    admin.render()
else:
    founder.render()
