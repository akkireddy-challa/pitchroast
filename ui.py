"""PitchRoast presentation layer — the kinetic UI from SPEC.md §2.

This module is pure presentation. It makes no API calls and holds no state; it
renders the dataclasses `syndicate.py` already produces (`Partner`,
`PartnerResult`, `SharkVerdict`). `app.py` stays the orchestrator and owns the
`convene()` lifecycle.

Division of labour with the theme:

    .streamlit/config.toml  →  colour, font, radius, borders   (the palette)
    ui.py                   →  motion, depth, entrances        (the choreography)

`config.toml` remains the source of truth for the palette. The one `<style>`
block injected by `inject_flair()` is limited to the five named micro-
interactions SPEC.md §2 specifies as product requirements — `pulseGlow`,
`flameFlicker`, `ledBlink`, `slideUpFade`, `hoverElevation` — plus the
glassmorphism surface and the tilted verdict stamp from the same section.

Two hard rules, both guarding live defects:

1. Model-generated text is NEVER interpolated into HTML. Critiques, zingers,
   valuations and covenants go through `st.markdown` / `st.metric` as text. The
   HTML below is static chrome plus values that originate in our own source
   (partner names, accents, icons) — and those are escaped anyway.
2. No `use_container_width`; it is deprecated. Widths use `width="stretch"`.

This module is imported, never run. `streamlit run app.py` is the only
entrypoint; there used to be a second one here (a component gallery with fake
data) and having two runnable Streamlit files meant the demo could be started
on the wrong one. Component behaviour is covered by `test_ui.py` instead.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:  # pragma: no cover - typing only
    from syndicate import Partner, PartnerResult, SharkVerdict

# --------------------------------------------------------------------------
# Key convention
# --------------------------------------------------------------------------
# Streamlit turns `key="partner_marc"` into the CSS class `.st-key-partner_marc`.
# That class is the only hook the stylesheet has, so the key convention is
# exported as a function rather than written out at each call site — app.py and
# the stylesheet then cannot drift apart.

# One namespace per lifecycle state, NOT one per partner. This is load-bearing:
# a partner's slot is re-rendered in place as waiting -> running -> done within
# a single script run, and Streamlit raises StreamlitDuplicateElementKey if the
# same key is registered twice in one run — even when the second render replaces
# the first inside the same st.empty(). Verified against Streamlit 1.64.
CARD_NS = "partner_"
WAITING_NS = "waiting_"
RUNNING_NS = "running_"

# Maps `draw_partner`-style status strings onto the namespace for that state.
_NS_BY_STATUS = {
    "waiting": WAITING_NS,
    "running": RUNNING_NS,
    "done": CARD_NS,
}


def slot_key(partner: Partner, status: str = "done") -> str:
    """The `key=` for this partner's card in a given lifecycle state.

    `status` is one of `"waiting"`, `"running"` or `"done"`, matching the
    `partner_start` / `partner_done` events from `convene`. Unknown values fall
    back to the card namespace.

    Always derive the key from this function rather than hand-writing it: the
    generated stylesheet builds its per-partner rules from the same mapping, so
    the keys and the CSS cannot drift apart.
    """
    return f"{_NS_BY_STATUS.get(status, CARD_NS)}{partner.id}"


def card_key(partner: Partner) -> str:
    """The `key=` for a partner's LANDED card — the state that animates in."""
    return slot_key(partner, "done")


def seat_key(partner: Partner) -> str:
    """The `key=` for a partner's seat while its call is still in flight."""
    return slot_key(partner, "running")


# Any card in any namespace picks up the shared surface treatment, so a card
# with an unexpected key still renders correctly — it only loses its accent tint.
_CARD_SCOPE = f'[class*="st-key-{CARD_NS}"]'
_SEAT_SCOPE = f'[class*="st-key-{WAITING_NS}"], [class*="st-key-{RUNNING_NS}"]'
_SCOPE = f"{_CARD_SCOPE}, {_SEAT_SCOPE}"


def _sel(scope: str, suffix: str = "") -> str:
    """Append a suffix to every selector in a comma-separated scope.

    `"a, b"` + `":hover"` must become `"a:hover, b:hover"`, not `"a, b:hover"` —
    concatenating onto the raw string silently drops all but the last selector.
    """
    return ", ".join(part.strip() + suffix for part in scope.split(","))

_FALLBACK_ACCENT = "#FF8C00"
_FALLBACK_ICON = "person"

# SPEC.md §2 — the signature fire gradient and the consensus-green LED.
_FIRE = ("#FF4500", "#FF8C00", "#FFD700")
_LED_GREEN = "#10B981"

# Entrance delays are keyed to the partner's declared order, not its render
# index, so a card animates the same whether it lands first or last.
_STAGGER_MS = 110


# --------------------------------------------------------------------------
# Stylesheet
# --------------------------------------------------------------------------

_KEYFRAMES = """
/* SPEC.md §2 — kinetic micro-interactions, by their specified names. */

@keyframes slideUpFade {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 15px rgba(255, 69, 0, 0.20); }
    50%      { box-shadow: 0 0 30px rgba(255, 69, 0, 0.50); }
}
@keyframes flameFlicker {
    0%, 100% { transform: scale(1) rotate(0deg);     filter: brightness(1); }
    25%      { transform: scale(1.05) rotate(-2deg); filter: brightness(1.15); }
    75%      { transform: scale(0.97) rotate(2deg);  filter: brightness(0.95); }
}
@keyframes ledBlink {
    0%, 100% { opacity: 1;    transform: scale(1); }
    50%      { opacity: 0.40; transform: scale(0.85); }
}

/* Supporting motion: the waiting seat and the stamp impact. */
@keyframes prSweep {
    from { background-position: -160% 0; }
    to   { background-position: 260% 0; }
}
@keyframes prBreathe {
    0%, 100% { opacity: 0.45; }
    50%      { opacity: 1; }
}
@keyframes stampSlam {
    0%   { opacity: 0; transform: rotate(-14deg) scale(2.6); }
    55%  { opacity: 1; transform: rotate(-5deg) scale(0.94); }
    72%  { transform: rotate(-5deg) scale(1.04); }
    100% { opacity: 1; transform: rotate(-5deg) scale(1); }
}
"""


def _stagger_rules(partners: tuple[Any, ...]) -> str:
    """Per-partner entrance delay and accent, for both key namespaces."""
    rules = []
    for i, p in enumerate(partners):
        accent = escape(str(getattr(p, "accent", _FALLBACK_ACCENT)), quote=True)
        for status in _NS_BY_STATUS:
            rules.append(
                f".st-key-{slot_key(p, status)} "
                f"{{ --pr-accent: {accent}; --pr-delay: {i * _STAGGER_MS}ms; }}"
            )
    return "\n".join(rules)


def inject_flair(partners: tuple[Any, ...] | None = None) -> None:
    """Install the animation layer. Call once, right after `st.set_page_config`.

    Entirely optional: every component below renders correctly without it, just
    without motion or the glass surface.
    """
    if partners is None:
        try:
            from syndicate import ALL_PARTNERS

            partners = ALL_PARTNERS
        except ImportError:  # pragma: no cover - keeps the preview standalone
            partners = ()

    fire_a, fire_b, fire_c = _FIRE

    st.html(f"""
<style>
{_KEYFRAMES}
{_stagger_rules(partners)}

/* --- Partner cards ---------------------------------------------------- */
/* Decorates the native st.container(border=True) rather than replacing it. */
/* SPEC §2: dark glassmorphism — translucent layer over the deep background. */
{_SCOPE} {{
    position: relative;
    overflow: hidden;
    background: rgba(30, 41, 59, 0.70);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transform-style: preserve-3d;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
}}

/* slideUpFade: the entrance plays only on the CARD namespace, so a seat that  */
/* cycles waiting -> running -> done animates once, when the verdict lands,    */
/* rather than re-firing on every state change. The :has() guard additionally  */
/* excludes our own skeleton if a caller reuses the card key for a placeholder.*/
{_sel(_CARD_SCOPE, ":not(:has(.pr-skeleton))")} {{
    animation: slideUpFade 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
    animation-delay: var(--pr-delay, 0ms);
}}

/* hoverElevation: -4px lift with 3D perspective & warm glow border, per spec. */
{_sel(_SCOPE, ":hover")} {{
    transform: translateY(-4px) perspective(900px) rotateX(1.8deg);
    border-color: var(--pr-accent, {fire_b});
    box-shadow: 0 16px 36px -8px rgba(0, 0, 0, 0.7), 0 0 20px var(--pr-accent, {fire_b});
}}

/* The accent reads as a top hairline, so the theme's borderColor still owns  */
/* the card's actual edge. Driven by --pr-accent from the key rules above, so */
/* it works for ANY container carrying a card_key()/seat_key() key — callers  */
/* do not have to use the components below to get the accent treatment.       */
{_sel(_SCOPE, "::before")} {{
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 2px;
    z-index: 1;
    background: linear-gradient(90deg,
        var(--pr-accent, {fire_b}) 0%, transparent 85%);
}}
/* A seat still waiting on its partner's call breathes. */
{_sel(_SEAT_SCOPE, "::before")} {{ animation: prBreathe 1.5s ease-in-out infinite; }}

/* --- The waiting seat -------------------------------------------------- */
.pr-skeleton {{
    height: 0.62rem;
    border-radius: 999px;
    margin: 0.55rem 0;
    background: linear-gradient(90deg,
        rgba(255, 255, 255, 0.05) 0%,
        rgba(255, 255, 255, 0.16) 45%,
        rgba(255, 255, 255, 0.05) 90%);
    background-size: 220% 100%;
    animation: prSweep 1.5s linear infinite;
}}
.pr-skeleton.pr-w80 {{ width: 80%; }}
.pr-skeleton.pr-w60 {{ width: 60%; }}

/* --- Hero -------------------------------------------------------------- */
/* pulseGlow: the boardroom furnace breathing behind the masthead. */
.pr-hero {{
    text-align: center;
    padding: 2.1rem 1.5rem 1.7rem;
    border-radius: 20px;
    margin-bottom: 1.6rem;
    border: 1px solid rgba(255, 69, 0, 0.30);
    background: radial-gradient(circle at 50% 0%,
        rgba(255, 69, 0, 0.18) 0%, rgba(15, 23, 42, 0.60) 75%);
    animation: pulseGlow 4s ease-in-out infinite;
}}
.pr-flame {{
    font-size: 3rem;
    line-height: 1;
    display: inline-block;
    transform-origin: 50% 90%;
    animation: flameFlicker 2.5s ease-in-out infinite;
}}
.pr-wordmark {{
    font-size: clamp(2rem, 5vw, 3rem);
    font-weight: 800;
    letter-spacing: -0.035em;
    margin: 0.35rem 0 0.4rem;
    background: linear-gradient(90deg, {fire_a} 0%, {fire_b} 50%, {fire_c} 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.pr-tagline {{
    max-width: 62ch;
    margin: 0 auto 0.95rem;
    opacity: 0.80;
    font-size: 1.1rem;
    line-height: 1.5;
}}
/* ledBlink: green status light signifying active model consensus. */
.pr-live {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 0.33rem 0.9rem;
    border-radius: 999px;
    border: 1px solid rgba(16, 185, 129, 0.30);
    background: rgba(16, 185, 129, 0.12);
    color: {_LED_GREEN};
    font-size: 0.8rem; font-weight: 700;
    letter-spacing: 0.045em; text-transform: uppercase;
}}
.pr-led {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {_LED_GREEN};
    box-shadow: 0 0 8px {_LED_GREEN};
    animation: ledBlink 1.8s ease-in-out infinite;
}}

/* --- Verdict stamp ------------------------------------------------------ */
/* SPEC §2: tilted, distressed stamp badge with a neon border glow. */
.pr-stamp-wrap {{ display: flex; justify-content: center; padding: 0.5rem 0 1.2rem; }}
.pr-stamp {{
    position: relative;
    border: 3px solid var(--pr-stamp);
    color: var(--pr-stamp);
    border-radius: 8px;
    padding: 0.45rem 1.3rem;
    font-size: clamp(1rem, 2.4vw, 1.35rem);
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    box-shadow: 0 0 14px -1px var(--pr-stamp);
    animation: stampSlam 0.75s cubic-bezier(0.2, 0.9, 0.3, 1.2) both;
}}
/* The "distressed" ink: irregular translucent streaks eaten out of the pad. */
.pr-stamp::after {{
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 8px;
    pointer-events: none;
    background: repeating-linear-gradient(
        74deg,
        rgba(0, 0, 0, 0.36) 0px, rgba(0, 0, 0, 0.36) 2px,
        transparent 2px, transparent 6px,
        rgba(0, 0, 0, 0.26) 6px, rgba(0, 0, 0, 0.26) 7px,
        transparent 7px, transparent 13px);
    mix-blend-mode: multiply;
    opacity: 0.55;
}}

/* --- Modern 2026 UI Design System ----------------------------------- */
.stApp {{
    background: radial-gradient(circle at 10% 10%, rgba(255, 69, 0, 0.05) 0%, transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(56, 189, 248, 0.04) 0%, transparent 45%),
                #0B1120 !important;
}}

button[kind="primary"] {{
    background: linear-gradient(135deg, #FF4500 0%, #EA580C 50%, #C2410C 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 4px 18px rgba(255, 69, 0, 0.35) !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    border-radius: 10px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
button[kind="primary"]:hover {{
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 25px rgba(255, 69, 0, 0.55) !important;
    border-color: rgba(255, 255, 255, 0.45) !important;
}}
button[kind="primary"]:active {{
    transform: translateY(0px) scale(0.99) !important;
}}

button[kind="secondary"] {{
    background: rgba(30, 41, 59, 0.55) !important;
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    backdrop-filter: blur(8px) !important;
    border-radius: 10px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
button[kind="secondary"]:hover {{
    background: rgba(255, 69, 0, 0.12) !important;
    border-color: rgba(255, 140, 0, 0.50) !important;
    color: #F8FAFC !important;
    transform: translateY(-2px) !important;
}}

.stDownloadButton > button {{
    background: rgba(30, 41, 59, 0.65) !important;
    border: 1px solid rgba(255, 140, 0, 0.35) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
.stDownloadButton > button:hover {{
    background: rgba(255, 140, 0, 0.18) !important;
    border-color: rgba(255, 140, 0, 0.80) !important;
    box-shadow: 0 4px 16px rgba(255, 140, 0, 0.25) !important;
    transform: translateY(-2px) !important;
}}

.stTextArea textarea {{
    background: rgba(15, 23, 42, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(12px) !important;
    color: #F8FAFC !important;
    font-family: inherit !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}
.stTextArea textarea:focus {{
    border-color: #FF8C00 !important;
    box-shadow: 0 0 16px rgba(255, 140, 0, 0.25) !important;
}}

div[data-testid="stMetric"] {{
    background: rgba(22, 30, 49, 0.65) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stMetric"]:hover {{
    border-color: rgba(255, 140, 0, 0.40) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.6) !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    border-color: rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(8px) !important;
}}

[data-testid="stSidebar"] {{
    background: #080D18 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}}
[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background: rgba(22, 30, 49, 0.50) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    transition: border-color 0.2s ease, transform 0.2s ease !important;
}}
[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{
    border-color: rgba(255, 140, 0, 0.35) !important;
    transform: translateY(-1px) !important;
}}

div[data-testid="stExpander"] {{
    background: rgba(22, 30, 49, 0.40) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
}}

div[data-testid="stSegmentedControl"] {{
    background: rgba(15, 23, 42, 0.70) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 999px !important;
    padding: 3px !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4) !important;
}}
div[data-testid="stSegmentedControl"] button {{
    border-radius: 999px !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    padding: 6px 14px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}
div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
    background: linear-gradient(135deg, rgba(255, 69, 0, 0.35) 0%, rgba(255, 140, 0, 0.45) 100%) !important;
    color: #FFF !important;
    border: 1px solid rgba(255, 140, 0, 0.60) !important;
    box-shadow: 0 0 12px rgba(255, 69, 0, 0.35) !important;
}}

div[data-testid="stAlert"] {{
    border-radius: 12px !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}}

div[data-testid="stSlider"] [role="slider"] {{
    background-color: #FF8C00 !important;
    border: 2px solid #FFF !important;
    box-shadow: 0 0 10px rgba(255, 140, 0, 0.6) !important;
}}

/* Code Terminal Styling */
.stCode {{
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    background: #080D18 !important;
}}

/* Dataframe styling */
[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    overflow: hidden !important;
}}

/* Progress bar neon styling */
div[data-testid="stProgressBar"] > div > div > div > div {{
    background: linear-gradient(90deg, #FF4500, #FF8C00, #10B981) !important;
    box-shadow: 0 0 12px rgba(255, 140, 0, 0.4) !important;
    border-radius: 999px !important;
}}



/* --- Accessibility ------------------------------------------------------ */
/* Motion here is decoration. Anyone who asks for less gets the static layout. */
@media (prefers-reduced-motion: reduce) {{
    {_SCOPE},
    {_sel(_SCOPE, "::before")},
    .pr-flame, .pr-led, .pr-hero, .pr-skeleton, .pr-stamp {{
        animation: none !important;
        transition: none !important;
    }}
    {_sel(_SCOPE, ":hover")} {{ transform: none; }}
    .pr-stamp {{ transform: rotate(-5deg); }}
}}
</style>
""")


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------


def hero(
    *,
    title: str = "PitchRoast Syndicate",
    tagline: str = (
        "Four autonomous AI venture partners debate, dismantle, and deliver the "
        "brutal truth no VC says to your face."
    ),
    status: str = "Autonomous committee ready · Stockholm build day",
    live: bool = True,
) -> None:
    """Animated masthead: flickering flame, fire-gradient wordmark, LED pill."""
    led = '<span class="pr-led"></span>' if live else ""
    st.html(f"""
<div class="pr-hero">
  <div class="pr-flame">&#128293;</div>
  <div class="pr-wordmark">{escape(title)}</div>
  <div style="font-size: 0.85rem; color: #FBBF24; font-weight: 700; margin-top: 4px; margin-bottom: 6px;">✨ Built with Claude by Akkireddy Challa</div>
  <div class="pr-tagline">{escape(tagline)}</div>
  <div class="pr-live">{led}{escape(status)}</div>
</div>
""")


def _heading(partner: Partner) -> None:
    """Icon, name and title row — shared by the waiting seat and the filed card."""
    icon = getattr(partner, "icon", _FALLBACK_ICON)
    row = st.container(horizontal=True, vertical_alignment="center", gap="small")
    row.markdown(f":material/{icon}:")
    row.markdown(f"**{partner.name}**")
    st.caption(partner.title)


def pending_card(
    partner: Partner,
    *,
    status: str = "running",
    key: str | None = None,
) -> None:
    """An empty seat, rendered while this partner's call is still in flight.

    Drive this from `convene`'s `on_event`: render on `partner_start`, then
    overwrite the same slot with `partner_card` on `partner_done`. The three
    seats then visibly fill in one at a time as the parallel calls return.

    `status` is `"waiting"` (queued, not yet called) or `"running"` (call in
    flight). It selects the key namespace as well as the copy, so rendering
    both states into one slot does not collide.

    Deliberately matches `partner_card`'s outer shape so the swap is seamless,
    and deliberately carries no `slideUpFade` — the entrance belongs to the card
    that lands, not to the placeholder.
    """
    with st.container(border=True, key=key or slot_key(partner, status)):
        _heading(partner)
        if status == "waiting":
            st.badge("Queued", icon=":material/hourglass_empty:", color="gray")
            st.caption(partner.focus)
            return
        st.html(
            '<div class="pr-skeleton"></div>'
            '<div class="pr-skeleton pr-w80"></div>'
            '<div class="pr-skeleton pr-w60"></div>'
        )
        st.caption(":shimmer[Reading the deck…]")


def partner_card(result: PartnerResult, *, key: str | None = None) -> None:
    """A filed verdict: critique, zinger pull-quote, and this partner's scores.

    A recused partner degrades to a visible empty chair with its error, rather
    than vanishing from the committee.
    """
    partner = result.partner
    with st.container(border=True, key=key or card_key(partner)):
        _heading(partner)

        # `verdict is None` is exactly the recused case.
        if result.verdict is None:
            st.badge("Recused", icon=":material/person_off:", color="gray")
            st.caption(result.error or "No verdict filed.")
            return

        v = result.verdict
        st.badge("Verdict filed", icon=":material/gavel:", color="red")

        # Model output goes through native elements only — never the HTML above.
        st.markdown(v.critique)
        st.markdown(f"> *“{v.zinger}”*")

        scores = st.container(horizontal=True, gap="medium")
        scores.metric("Delusion", v.delusion_index, format="%d%%")
        scores.metric("Moat", f"{v.moat_score}/10")
        scores.metric("Runway", f"{v.runway_months} mo")

        if result.latency_s:
            st.caption(
                f":material/timer: {result.latency_s:.1f}s · "
                f"{result.input_tokens + result.output_tokens:,} tokens"
            )


def scorecard(shark: SharkVerdict) -> None:
    """The committee's reconciled numbers as four bordered metrics."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Delusion index", shark.delusion_index, format="%d%%", border=True,
              help="How far the pitch sits from observable reality.")
    c2.metric("True moat", f"{shark.moat_score}/10", border=True,
              help="What actually stops a competent team cloning this in a weekend.")
    c3.metric("Survival runway", f"{shark.runway_months} mo", border=True,
              help="Months before an emergency bridge round.")
    c4.metric("Pre-money", shark.pre_money_val, border=True,
              help="The committee's non-negotiable haircut.")


def verdict_stamp(funded: bool) -> None:
    """The tilted, distressed rubber stamp that slams down over the term sheet."""
    if funded:
        label, colour = "✅ Funded by syndicate", _LED_GREEN
    else:
        label, colour = "❌ Rejected by syndicate", "#EF4444"
    st.html(
        f'<div class="pr-stamp-wrap">'
        f'<div class="pr-stamp" style="--pr-stamp: {colour};">{escape(label)}</div>'
        f"</div>"
    )
