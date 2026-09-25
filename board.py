"""The boardroom: rendering a verdict, and the live run that produces one.

Shared by both entry points. The Hot Seat draws the same cards the Observatory
does — the difference is one flag. `technical=False` (the founder default)
suppresses the reasoning drawers, the per-card latency/token footers and the
run footer; the Observatory turns them back on and adds its own instruments on
top. Everything else — the cards, the scorecard, the term sheet — is identical,
so a verdict looks the same in both views and only the annotations change.

Model-produced text is never rendered as HTML. Every string that came back from
the API goes through a native element (`st.markdown` with HTML disabled,
`st.metric`, `st.badge`, `st.caption`), so there is no injection surface here.
"""

from __future__ import annotations

import logging

import streamlit as st

import state
from syndicate import (
    PARTNERS,
    SHARK,
    Event,
    Partner,
    PartnerResult,
    SyndicateError,
    SyndicateResult,
    convene,
    term_sheet_text,
)
from ui import slot_key, verdict_stamp

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------


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
    technical: bool = False,
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

        if technical:
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


def draw_term_sheet(result: SyndicateResult, *, technical: bool = False) -> None:
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
    # The export's footer line names the model and the token count. Fine inside
    # a file the founder keeps; not fine rendered on the founder's screen, which
    # is the one place that footer would be visible. Operators get the preview.
    if technical:
        with st.expander("Plain-text term sheet", icon=":material/description:"):
            st.code(export, language="text", wrap_lines=True)


def draw_shark(slot, result: SyndicateResult, *, technical: bool = False) -> None:
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
        if technical:
            draw_thinking(result.shark_thinking, "Managing partner deliberation")

        st.subheader("Scorecard", icon=":material/scoreboard:")
        draw_scorecard(result)

        st.subheader("Deal terms", icon=":material/contract:")
        draw_term_sheet(result, technical=technical)


def draw_result(result: SyndicateResult, *, technical: bool = False) -> None:
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
    # Drive the columns off the result, not the global roster: the panel can be
    # trimmed in the Observatory, and a stored result from a two-partner run
    # must not be rendered against three columns (zip(strict=True) would raise).
    filed = result.partners
    cols = st.columns(len(filed))
    for col, item in zip(cols, filed, strict=True):
        draw_partner(col.empty(), item.partner, item, status="done", technical=technical)

    st.subheader("Managing partner's verdict", icon=":material/gavel:")
    if result.shark is None and result.error:
        st.error(result.error, icon=":material/error:")
        st.caption("Check the API key and remaining credits, then convene again.")
    draw_shark(st.empty(), result, technical=technical)

    if technical:
        st.caption(
            f":material/bolt: {result.total_tokens:,} tokens "
            f"({result.input_tokens:,} in / {result.output_tokens:,} out) · "
            f"{result.latency_s:.1f}s · model `{result.model}`"
        )


# --------------------------------------------------------------------------
# The live run
# --------------------------------------------------------------------------


def run_committee(
    pitch: str,
    *,
    api_key: str,
    model_id: str,
    brutality: float,
    effort: str,
    panel: list[str],
    technical: bool = False,
) -> None:
    """Reserve the card slots, stream progress into them, then persist the result.

    Ends in `st.rerun()`, so nothing after the call site runs. The authoritative
    render happens from session state on the rerun — which is also what makes
    the verdict survive a flip to the other view.
    """
    seats = [p for p in PARTNERS if p.id in set(panel)]

    st.subheader("The boardroom debate", icon=":material/forum:")
    cols = st.columns(len(seats))
    slots = {}
    for col, partner in zip(cols, seats, strict=True):
        slot = col.empty()
        draw_partner(slot, partner, status="waiting", technical=technical)
        slots[partner.id] = slot

    st.subheader("Managing partner's verdict", icon=":material/gavel:")
    shark_slot = st.empty()
    shark_slot.markdown(":shimmer[Waiting on the partners…]")

    def on_event(event: Event) -> None:
        # Best effort. convene() runs the partners concurrently, so this may be
        # invoked off the main script thread where st.* calls are inert. The
        # authoritative render happens from session state after the rerun.
        try:
            if event.kind == "partner_start" and event.partner is not None:
                draw_partner(
                    slots[event.partner.id],
                    event.partner,
                    status="running",
                    technical=technical,
                )
            elif event.kind == "partner_done" and event.result is not None:
                draw_partner(
                    slots[event.result.partner.id],
                    event.result.partner,
                    event.result,
                    status="done",
                    technical=technical,
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
    st.session_state.running = True
    try:
        with st.spinner("Convening the committee…", show_time=True):
            try:
                result = convene(
                    pitch,
                    api_key=api_key,
                    model=model_id,
                    brutality=brutality,
                    effort=effort,
                    panel=panel,
                    on_event=on_event,
                )
            except SyndicateError as exc:
                failure = str(exc)
    finally:
        # Must clear in a finally: a RerunException (BaseException, so it slips
        # past the except above) would otherwise leave the button disabled for
        # the rest of the session.
        st.session_state.running = False

    st.session_state.result = result
    st.session_state.setup_error = failure
    if result is not None:
        # Costed here rather than in the view, so a run started from either
        # entry point shows up in the Observatory's telemetry exactly once.
        state.record_spend(result)
    st.rerun()
