"""PitchRoast — a satirical AI venture committee that roasts your startup pitch.

All model orchestration lives in ``syndicate.py``. This file is the Streamlit
surface only: controls, live progress, and rendering of a ``SyndicateResult``.

Model-produced text is never rendered as HTML. Every string that came back from
the API goes through a native element (``st.markdown`` with HTML disabled,
``st.metric``, ``st.badge``, ``st.caption``), so there is no injection surface.
The only custom HTML in the app is the static hero banner below.
"""

from __future__ import annotations

import logging
import os

import streamlit as st
from dotenv import load_dotenv

from syndicate import (
    DEFAULT_MODEL,
    MODELS,
    PARTNERS,
    SHARK,
    Event,
    Partner,
    PartnerResult,
    SyndicateError,
    SyndicateResult,
    convene,
    setup_observability,
    term_sheet_text,
)
from ui import hero, inject_flair, slot_key, verdict_stamp

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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRESETS: dict[str, str] = {
    "☕ Autonomous Oat Milk Micro-Roastery with Web3 Proof-of-Foam": (
        "A decentralized network of countertop espresso machines that roast "
        "small-batch Nordic oat milk using on-chain temperature consensus. "
        "Users stake OAT tokens for latte art NFTs. Market size: $400B "
        "addressable beverage space."
    ),
    "🤖 AI Meeting Proxy that says 'Blocked by Backend' in 14 accents": (
        "An autonomous AI agent avatar that joins daily Scrum standups on "
        "Zoom/Teams, randomly sighs, checks its phone, and responds 'I am "
        "blocked by the infrastructure backend' whenever your name is called. "
        "B2B SaaS priced at $49/engineer/month."
    ),
    "🐾 Uber for Cats: Feline Scooter On-Demand": (
        "High-density urban cat affection. When an office worker feels burnt "
        "out, our app dispatches an autonomous electric scooter carrying a "
        "pre-vetted emotional support cat to their office lobby for a "
        "15-minute petting session."
    ),
    "🍕 Tinder for Leftover Pizza: Peer-to-Peer Slice Swapping": (
        "A location-based peer-to-peer marketplace where college students "
        "swipe right on half-eaten pizza slices in nearby dorm rooms. Powered "
        "by zero-knowledge crust verification."
    ),
}

MODEL_LABELS: list[str] = list(MODELS)
DEFAULT_MODEL_INDEX: int = next(
    (i for i, label in enumerate(MODEL_LABELS) if MODELS[label] == DEFAULT_MODEL),
    0,
)

# The single piece of custom HTML in the app: a static hero banner. It contains
# no interpolation, so nothing model-derived can reach the DOM here.
HERO = """
<style>
  .pr-hero {
    position: relative;
    overflow: hidden;
    text-align: center;
    padding: 2rem 1.5rem 1.6rem;
    margin-bottom: 1.2rem;
    border: 1px solid rgba(255, 69, 0, 0.32);
    border-radius: 18px;
    background:
      radial-gradient(120% 140% at 50% 0%, rgba(255, 69, 0, 0.20) 0%, rgba(11, 15, 25, 0) 70%),
      linear-gradient(180deg, rgba(20, 26, 39, 0.9) 0%, rgba(11, 15, 25, 0.9) 100%);
  }
  .pr-hero__kicker {
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #FFB627;
    opacity: 0.85;
  }
  .pr-hero__title {
    font-size: clamp(2.2rem, 5vw, 3.1rem);
    font-weight: 800;
    letter-spacing: -0.035em;
    line-height: 1.1;
    margin: 0.35rem 0 0.5rem;
    background: linear-gradient(90deg, #FF4500 0%, #FF8C00 50%, #FFD700 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .pr-hero__sub {
    max-width: 760px;
    margin: 0 auto;
    font-size: 1.05rem;
    line-height: 1.5;
    color: #C3CCDB;
  }
  @media (prefers-reduced-motion: no-preference) {
    .pr-hero { animation: pr-ember 5s ease-in-out infinite; }
    @keyframes pr-ember {
      0%, 100% { box-shadow: 0 0 18px rgba(255, 69, 0, 0.16); }
      50%      { box-shadow: 0 0 34px rgba(255, 69, 0, 0.38); }
    }
  }
</style>
<div class="pr-hero">
  <div class="pr-hero__kicker">Autonomous venture committee</div>
  <div class="pr-hero__title">PitchRoast 🔥</div>
  <div class="pr-hero__sub">
    Three AI partners tear your pitch apart in parallel. Then the shark
    reconciles the scorecard and writes a term sheet you did not ask for.
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Observability (cached so Streamlit reruns never launch a second Phoenix)
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def phoenix_url() -> str | None:
    """Start local Phoenix tracing once per server process."""
    return setup_observability()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

st.session_state.setdefault("pitch_text", "")
st.session_state.setdefault("result", None)
st.session_state.setdefault("setup_error", None)


def load_preset() -> None:
    """Copy the chosen demo pitch into the text area."""
    label = st.session_state.get("preset_choice")
    if label:
        st.session_state.pitch_text = PRESETS[label]


def clear_all() -> None:
    """Reset the pitch and any previous verdict."""
    st.session_state.pitch_text = ""
    st.session_state.preset_choice = None
    st.session_state.result = None
    st.session_state.setup_error = None


# ---------------------------------------------------------------------------
# Rendering helpers — native elements only, no HTML
# ---------------------------------------------------------------------------


def draw_thinking(thinking: str, label: str) -> None:
    """Compact reasoning drawer. Stays silent when there is nothing to show."""
    if not thinking.strip():
        return
    with st.expander(label, type="compact", icon=":material/psychology:"):
        st.markdown(thinking)


def draw_partner(
    slot,
    partner: Partner,
    result: PartnerResult | None = None,
    *,
    status: str = "waiting",
) -> None:
    """Render (or re-render) one partner card into a reserved placeholder."""
    # Key must be namespaced by status, not just partner: this slot is drawn up
    # to three times per script run (waiting -> running -> done) and Streamlit
    # raises StreamlitDuplicateElementKey on a repeated key within one run, even
    # when the second render replaces the first inside the same st.empty().
    with slot.container(border=True, height="stretch", key=slot_key(partner, status)):
        st.markdown(f":material/{partner.icon}: **{partner.name}**")
        st.caption(partner.title)

        if status == "waiting":
            st.badge("Queued", icon=":material/hourglass_empty:", color="gray")
            st.caption(partner.focus)
            return

        if status == "running":
            st.markdown(":shimmer[Reading the pitch…]")
            st.caption(partner.focus)
            return

        if result is None:
            st.badge("No response", icon=":material/help:", color="gray")
            st.caption(partner.focus)
            return

        if result.recused:
            st.badge("Recused", icon=":material/person_off:", color="gray")
            st.markdown(f":gray[{result.error or 'Declined to vote on this one.'}]")
            return

        if result.verdict is None:
            st.badge("Errored", icon=":material/error:", color="red")
            st.markdown(f":gray[{result.error or 'No verdict returned.'}]")
            return

        verdict = result.verdict
        st.badge("Voted", icon=":material/how_to_vote:", color="orange")
        st.markdown(verdict.critique)
        st.markdown(f"*“{verdict.zinger}”*")

        with st.container(horizontal=True):
            st.badge(f"Delusion {verdict.delusion_index}%", color="red")
            st.badge(f"Moat {verdict.moat_score}/10", color="orange")
            st.badge(f"Runway {verdict.runway_months} mo", color="blue")

        draw_thinking(result.thinking, "Partner deliberation")
        st.caption(
            f"{result.latency_s:.1f}s · {result.input_tokens:,} in / "
            f"{result.output_tokens:,} out"
        )


def draw_scorecard(result: SyndicateResult) -> None:
    """The shark's four reconciled headline numbers."""
    verdict = result.shark
    if verdict is None:
        return
    cols = st.columns(4)
    cols[0].metric(
        "Delusion index",
        f"{verdict.delusion_index}%",
        border=True,
        height="stretch",
        help="Gap between the founder's claims and observable reality.",
    )
    cols[1].metric(
        "Moat score",
        f"{verdict.moat_score}/10",
        border=True,
        height="stretch",
        help="Resistance to being cloned over a weekend.",
    )
    cols[2].metric(
        "Runway",
        f"{verdict.runway_months} mo",
        border=True,
        height="stretch",
        help="Months before an emergency bridge round.",
    )
    with cols[3].container(border=True, height="stretch"):
        st.caption("Pre-money valuation")
        st.markdown(f"**{verdict.pre_money_val}**")


def draw_term_sheet(result: SyndicateResult) -> None:
    """Deal terms, covenants, the pivot, and the .txt export."""
    verdict = result.shark
    if verdict is None:
        return
    sheet = verdict.term_sheet

    with st.container(border=True):
        st.markdown("**Non-binding term sheet**")
        verdict_stamp(verdict.funded)
        cols = st.columns(3)
        terms = (
            ("Valuation", sheet.valuation),
            ("Investment", sheet.investment_amount),
            ("Liquidation preference", sheet.liquidation_pref),
        )
        for col, (label, value) in zip(cols, terms, strict=True):
            with col.container(border=True, height="stretch"):
                st.caption(label)
                st.markdown(f"**{value}**")

        st.caption("Mandatory founder covenants")
        for index, covenant in enumerate(sheet.covenants, start=1):
            st.markdown(f"{index}\\. {covenant}")

    st.info(verdict.the_pivot, icon=":material/lightbulb:")

    export = term_sheet_text(result)
    st.download_button(
        "Download term sheet",
        data=export,
        file_name="pitchroast_term_sheet.txt",
        mime="text/plain",
        icon=":material/download:",
    )
    with st.expander("Plain-text term sheet", icon=":material/description:"):
        st.code(export, language="text", wrap_lines=True)


def draw_shark(slot, result: SyndicateResult) -> None:
    """Render the managing partner's synthesis into a reserved placeholder."""
    with slot.container(border=True):
        st.markdown(f":material/{SHARK.icon}: **{SHARK.name}**")
        st.caption(SHARK.title)

        verdict = result.shark
        if verdict is None:
            st.badge("No synthesis", icon=":material/error:", color="red")
            if not result.error:
                st.caption("The managing partner returned no verdict.")
            return

        if verdict.funded:
            st.success("Term sheet offered", icon=":material/handshake:")
        else:
            st.error("Rejected by the syndicate", icon=":material/gavel:")

        st.markdown(f"*“{verdict.closing_line}”*")
        draw_thinking(result.shark_thinking, "Managing partner deliberation")

        st.subheader("Scorecard", icon=":material/scoreboard:")
        draw_scorecard(result)

        st.subheader("Deal terms", icon=":material/contract:")
        draw_term_sheet(result)


def draw_result(result: SyndicateResult) -> None:
    """Full, rerun-safe render of a stored SyndicateResult."""
    if result.refused:
        st.warning(
            "The committee has declined to take this meeting.",
            icon=":material/gavel:",
        )
        st.caption(
            result.refusal_reason
            or "Reword the pitch and the partners will reconvene."
        )
        return

    st.subheader("The boardroom debate", icon=":material/forum:")
    by_id = {item.partner.id: item for item in result.partners}
    cols = st.columns(len(PARTNERS))
    for col, partner in zip(cols, PARTNERS, strict=True):
        draw_partner(col.empty(), partner, by_id.get(partner.id), status="done")

    st.subheader("Managing partner's verdict", icon=":material/gavel:")
    if result.shark is None and result.error:
        st.error(result.error, icon=":material/error:")
        st.caption("Check the API key and remaining credits, then convene again.")
    draw_shark(st.empty(), result)

    st.caption(
        f":material/bolt: {result.total_tokens:,} tokens "
        f"({result.input_tokens:,} in / {result.output_tokens:,} out) · "
        f"{result.latency_s:.1f}s · model `{result.model}`"
    )


def run_committee(pitch: str, api_key: str, model_id: str, brutality: float) -> None:
    """Reserve the card slots, stream progress into them, then persist the result."""
    st.subheader("The boardroom debate", icon=":material/forum:")
    cols = st.columns(len(PARTNERS))
    slots = {}
    for col, partner in zip(cols, PARTNERS, strict=True):
        slot = col.empty()
        draw_partner(slot, partner, status="waiting")
        slots[partner.id] = slot

    st.subheader("Managing partner's verdict", icon=":material/gavel:")
    shark_slot = st.empty()
    shark_slot.markdown(":shimmer[Waiting on the partners…]")

    def on_event(event: Event) -> None:
        # Best effort. convene() runs the three partners concurrently, so this
        # may be invoked off the main script thread where st.* calls are inert.
        # The authoritative render happens from session state after the rerun.
        try:
            if event.kind == "partner_start" and event.partner is not None:
                draw_partner(slots[event.partner.id], event.partner, status="running")
            elif event.kind == "partner_done" and event.result is not None:
                draw_partner(
                    slots[event.result.partner.id],
                    event.result.partner,
                    event.result,
                    status="done",
                )
            elif event.kind == "shark_start":
                shark_slot.markdown(f":shimmer[{SHARK.name} is drafting the terms…]")
            elif event.kind == "shark_done":
                shark_slot.markdown(":shimmer[Stamping the paperwork…]")
        except Exception:
            # Progress is decorative; never let it take the run down.
            logger.debug("Live progress update skipped", exc_info=True)

    failure: str | None = None
    result: SyndicateResult | None = None
    with st.spinner("Convening the committee…", show_time=True):
        try:
            result = convene(
                pitch,
                api_key=api_key,
                model=model_id,
                brutality=brutality,
                on_event=on_event,
            )
        except SyndicateError as exc:
            failure = str(exc)

    st.session_state.result = result
    st.session_state.setup_error = failure
    st.rerun()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

hero()

tracing_url = phoenix_url()

with st.sidebar:
    st.subheader("Syndicate controls", icon=":material/tune:")

    api_key = st.text_input(
        "Anthropic API key",
        type="password",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        help="Read from ANTHROPIC_API_KEY / .env by default. Never logged.",
    )

    model_label = st.selectbox(
        "Model",
        MODEL_LABELS,
        index=DEFAULT_MODEL_INDEX,
        help="Use the fast model while iterating; switch up for the live demo.",
    )
    model_id = MODELS[model_label]

    brutality = st.slider(
        "Brutality index",
        min_value=0.0,
        max_value=1.0,
        value=0.85,
        step=0.05,
        help=(
            "Interpolated into the partners' system prompts. This is prompt "
            "text, not a sampling parameter."
        ),
    )

    st.subheader("Observability", icon=":material/timeline:")
    if tracing_url:
        st.link_button(
            "Open Phoenix traces",
            tracing_url,
            icon=":material/open_in_new:",
            width="stretch",
        )
        st.caption("Local OTEL spans: latency, tokens, prompts. No external cost.")
    else:
        st.caption("Phoenix tracing offline.")

    st.subheader("Committee", icon=":material/groups:")
    for member in (*PARTNERS, SHARK):
        st.markdown(f":material/{member.icon}: **{member.name}**")
        st.caption(member.title)

    st.caption("Built with Anthropic Claude for Stockholm Build Day at Epicenter.")


st.subheader("Submit a pitch", icon=":material/rocket_launch:")

st.selectbox(
    "Demo pitch",
    list(PRESETS),
    index=None,
    placeholder="Load one of the built-in demo pitches",
    key="preset_choice",
    on_change=load_preset,
)

st.text_area(
    "Pitch or executive summary",
    key="pitch_text",
    height=150,
    placeholder=(
        "Describe the product, the customer, the business model, and why "
        "nobody else can build it."
    ),
)

with st.container(horizontal=True):
    convene_clicked = st.button(
        "Convene the committee",
        type="primary",
        icon=":material/gavel:",
    )
    st.button("Clear", icon=":material/backspace:", on_click=clear_all)


# ---------------------------------------------------------------------------
# Dispatch: idle / no key / empty pitch / running / result
# ---------------------------------------------------------------------------

active_key = (api_key or "").strip() or os.getenv("ANTHROPIC_API_KEY", "").strip()
pitch_text = (st.session_state.pitch_text or "").strip()

should_run = False
if convene_clicked:
    if not active_key:
        st.error(
            "Add an Anthropic API key in the sidebar, or set ANTHROPIC_API_KEY.",
            icon=":material/key_off:",
        )
    elif not pitch_text:
        st.warning(
            "The committee needs something to roast. Write a pitch or load a demo.",
            icon=":material/edit_note:",
        )
    else:
        should_run = True

if st.session_state.setup_error and not should_run:
    st.error(st.session_state.setup_error, icon=":material/error:")

if should_run:
    run_committee(pitch_text, active_key, model_id, brutality)
elif st.session_state.result is not None:
    draw_result(st.session_state.result)
elif not convene_clicked:
    st.caption(
        "Load a demo pitch or write your own, then convene the committee. "
        "Three partners deliberate in parallel before the shark closes."
    )
