"""🎯 Founder Hot Seat — the entry point a founder is meant to see.

Everything on this page is about the pitch and the verdict. There is no API key
field, no model id, no Phoenix link, no token counter and no seat selector:
those are operator concerns, they break the illusion of a real board, and they
all live in the Syndicate Observatory instead.

The two dials that *are* here are the two a founder actually has an opinion
about — which pitch, and how hard they want to be hit.
"""

from __future__ import annotations

import streamlit as st

import board
import state
from syndicate import PARTNERS, SHARK
from ui import hero

# --------------------------------------------------------------------------
# Demo pitches
# --------------------------------------------------------------------------
# Short labels so they fit on pills; the long version is what the committee
# actually reads.

PRESETS: dict[str, str] = {
    "☕ Oat Milk Web3": (
        "A decentralized network of countertop espresso machines that roast "
        "small-batch Nordic oat milk using on-chain temperature consensus. "
        "Users stake OAT tokens for latte art NFTs. Market size: $400B "
        "addressable beverage space."
    ),
    "💳 Klarna for Regret": (
        "A Stockholm-born fintech that amortizes emotional trauma from impulsive "
        "life decisions into four interest-free, guilt-deferred installments. "
        "Whether you bought a 95 SEK oat cortado in Södermalm, joined an AI crypto "
        "startup, or drunk-texted an ex at 3 AM, our Swedish Open Banking algorithm "
        "stretches your shame over 60 days. Remorse-as-a-Service."
    ),
    "☕ FikaSync Compliance": (
        "An autonomous Swedish workplace compliance agent that enforces statutory "
        "work-life balance across engineering teams. If a developer pushes commits to "
        "GitHub or posts in Slack between 10:00–10:20 or 15:00–15:20 without taking "
        "their mandatory coffee and cinnamon bun (kanelbulle), FikaSync revokes their "
        "AWS production credentials and locks their IDE. Union-approved."
    ),
    "🤖 AI Standup Bot": (
        "An autonomous AI agent avatar that joins daily Scrum standups on "
        "Zoom/Teams, randomly sighs, checks its phone, and responds 'I am "
        "blocked by the infrastructure backend' whenever your name is called. "
        "B2B SaaS priced at $49/engineer/month."
    ),
    "🐾 Uber for Cats": (
        "High-density urban cat affection. When an office worker feels burnt "
        "out, our app dispatches an autonomous electric scooter carrying a "
        "pre-vetted emotional support cat to their office lobby for a "
        "15-minute petting session."
    ),
    "🍕 Tinder for Pizza": (
        "A location-based peer-to-peer marketplace where college students "
        "swipe right on half-eaten pizza slices in nearby dorm rooms. Powered "
        "by zero-knowledge crust verification."
    ),
}


def _load_preset() -> None:
    """Copy the chosen demo pitch into the text area."""
    label = st.session_state.get("preset_choice")
    if label:
        st.session_state.pitch_text = PRESETS[label]


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------


def _sidebar() -> None:
    seated = state.panel()

    with st.sidebar:
        st.subheader("Quick pitches", icon=":material/bolt:")
        st.pills(
            "Demo pitch",
            list(PRESETS),
            key="preset_choice",
            on_change=_load_preset,
            label_visibility="collapsed",
            disabled=st.session_state.running,
        )

        st.subheader("VC mood", icon=":material/mood:")
        # persist_state: the Observatory does not draw this widget, so without
        # it a flip to the other view and back would reset the founder's dial.
        chosen = st.select_slider(
            "How hard should they hit?",
            options=[m.label for m in state.MOODS],
            value=state.mood().label,
            key=state.K_MOOD,
            persist_state="session",
            label_visibility="collapsed",
            disabled=st.session_state.running,
        )
        st.caption(state.MOODS_BY_LABEL[chosen].blurb)

        st.subheader("The syndicate committee", icon=":material/groups:")
        for member in (*PARTNERS, SHARK):
            # The managing partner is never optional, so it never reads as an
            # empty chair even when the panel has been trimmed.
            attending = member is SHARK or member.id in seated
            with st.container(border=True):
                row = st.container(horizontal=True, vertical_alignment="center")
                row.markdown(f"## {member.emoji or '🎩'}")
                with row.container():
                    st.markdown(f"**{member.name}**")
                    st.caption(member.title)
                if attending:
                    st.caption(member.focus)
                else:
                    st.caption(":gray[Not attending today.]")

        st.caption("Built with Anthropic Claude for Stockholm Build Day at Epicenter.")


# --------------------------------------------------------------------------
# Main stage
# --------------------------------------------------------------------------


def render() -> None:
    """Draw the founder experience. Called once per rerun, by `app.py`."""
    seated = state.panel()
    _sidebar()

    hero(
        status=(
            f"{len(seated)} partners seated · {SHARK.name} closing"
            if seated
            else "Committee not seated"
        )
    )

    st.subheader("Your pitch", icon=":material/rocket_launch:")
    st.text_area(
        "Pitch or executive summary",
        key="pitch_text",
        height=170,
        label_visibility="collapsed",
        placeholder=(
            "Describe the product, the customer, the business model, and why "
            "nobody else can build it."
        ),
        disabled=st.session_state.running,
    )

    with st.container(horizontal=True):
        # `disabled` while a run is in flight: a second click mid-run raises
        # RerunException, which derives from BaseException and so slips past the
        # `except Exception` in run_committee. The rerun then blocks on the
        # pool's shutdown(wait=True) — the UI freezes and a second full run gets
        # paid for.
        face_them = st.button(
            "Face the syndicate",
            type="primary",
            icon=":material/gavel:",
            key="convene_btn",
            disabled=st.session_state.running,
        )
        st.button(
            "Clear",
            icon=":material/backspace:",
            key="clear_btn",
            on_click=state.clear_pitch,
            disabled=st.session_state.running,
        )

    pitch = state.pitch()

    should_run = False
    if face_them:
        if not pitch:
            st.warning(
                "The committee needs something to roast. Write a pitch or pick a "
                "quick one from the sidebar.",
                icon=":material/edit_note:",
            )
        elif not seated:
            st.warning(
                "Nobody is seated on the panel — the committee cannot convene.",
                icon=":material/person_off:",
            )
        elif not state.api_key():
            # Deliberately not "add an API key": a founder cannot act on that,
            # and naming the credential on a projector is worse than useless.
            st.error(
                "The syndicate is offline. Grab the operator.",
                icon=":material/cloud_off:",
            )
        else:
            should_run = True

    if st.session_state.setup_error and not should_run:
        st.error(
            "The committee could not be reached. Grab the operator.",
            icon=":material/cloud_off:",
        )

    if should_run:
        board.run_committee(
            pitch,
            api_key=state.api_key(),
            model_id=state.model_id(),
            brutality=state.brutality(),
            effort=state.effort(),
            panel=seated,
        )
    elif st.session_state.result is not None:
        board.draw_result(st.session_state.result)
    elif not face_them:
        st.caption(
            f"Pick a quick pitch or write your own, then face the syndicate. "
            f"{len(seated) or 'No'} partner{'s' if len(seated) != 1 else ''} "
            f"read it at the same time before {SHARK.name} writes the terms."
        )
