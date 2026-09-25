#!/usr/bin/env python3
"""Offline tests for the two entry points and the credit arithmetic.

No API key, no network, no Phoenix: `state.tracing()` is stubbed out and every
verdict below is a literal. What earns this file is the thing a human reviewer
cannot reliably check by eye before going on stage:

1. **Routing.** `?mode=admin` opens the Observatory, `?mode=founder` and
   anything unrecognised open the Hot Seat, and toggling writes the slug — not
   the emoji button label — back into the URL.
2. **Isolation.** The Hot Seat must leak none of the operator surface. A
   regression here is invisible in code review (one misplaced `st.caption`) and
   very visible on a projector.
3. **Shared state.** A verdict convened in one view has to still be there after
   the toggle, or the demo pays for a second roast on stage.
4. **Money.** The telemetry quotes euros at a judge. The arithmetic behind that
   number is worth a test.

Run: .venv/bin/python test_modes.py
"""

from __future__ import annotations

import os
import sys

from streamlit.testing.v1 import AppTest

import costs
import observability as obs
import syndicate as s

FAILURES: list[str] = []

# Generous: the first AppTest run imports streamlit, syndicate and anthropic.
TIMEOUT = 120


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}{f' — {detail}' if detail else ''}")
        FAILURES.append(name)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

THINKING = "THINKING_SENTINEL the deck is a mood board"


def _result() -> s.SyndicateResult:
    """A complete, successful roast — every panel has something to render."""
    partners = [
        s.PartnerResult(
            partner=p,
            verdict=s.PartnerVerdict(
                critique=f"{p.name} is unimpressed.",
                delusion_index=91,
                moat_score=1,
                runway_months=3,
                zinger="A landing page with a burn rate.",
            ),
            latency_s=4.0 + i,
            input_tokens=1000,
            output_tokens=500,
            thinking=THINKING,
        )
        for i, p in enumerate(s.PARTNERS)
    ]
    return s.SyndicateResult(
        pitch="Uber for cats.",
        model="claude-opus-5-5",
        partners=partners,
        shark=s.SharkVerdict(
            delusion_index=94,
            moat_score=1,
            runway_months=2,
            pre_money_val="$14.50 and a cold kanelbulle",
            term_sheet=s.TermSheet(
                valuation="$12.00",
                investment_amount="$500 in cloud credits",
                liquidation_pref="10x participating",
                covenants=["Apologise weekly", "No more decks", "Delete the coin"],
            ),
            the_pivot="Sell the telemetry to insurers.",
            funded=False,
            closing_line="The committee thanks you for the entertainment.",
        ),
        shark_thinking=THINKING,
        latency_s=9.0,
        input_tokens=4000,
        output_tokens=2000,
        session_id="deadbeefdeadbeef",
    )


# Element attributes worth scraping. AppTest exposes rendered text on different
# attributes per element type, so cast a wide net and join everything.
_KINDS = (
    "markdown", "caption", "text", "code", "subheader", "header", "title",
    "warning", "error", "info", "success", "metric", "button", "link_button",
    "text_input", "selectbox", "multiselect", "slider", "select_slider",
    "toggle", "expander", "segmented_control", "pills", "download_button",
    "html", "progress",
)
_ATTRS = ("value", "label", "body", "url", "help", "placeholder", "text", "options")


def page_text(at: AppTest) -> str:
    """Every string the page rendered, sidebar included."""
    out: list[str] = []
    for kind in _KINDS:
        try:
            elements = list(at.get(kind))
        except Exception:  # noqa: BLE001 - element type not present in this build
            continue
        for element in elements:
            for attr in _ATTRS:
                value = getattr(element, attr, None)
                if isinstance(value, str):
                    out.append(value)
                elif isinstance(value, (list, tuple)):
                    out.extend(v for v in value if isinstance(v, str))
    return "\n".join(out)


def run_app(*, mode: str | None = None, result=None) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    if mode is not None:
        at.query_params["mode"] = mode
    if result is not None:
        at.session_state["result"] = result
    at.run()
    return at


def is_admin(at: AppTest) -> bool:
    return any("Syndicate observatory" in t.value for t in at.title)


def url_mode(at: AppTest) -> str:
    """`?mode=` as the browser would show it. AppTest stores params as lists."""
    raw = at.query_params.get("mode")
    if isinstance(raw, (list, tuple)):
        return raw[0] if raw else ""
    return raw or ""


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_routing() -> None:
    print("\nRouting")
    for mode, expect_admin in (
        (None, False),
        ("founder", False),
        ("admin", True),
        ("ADMIN", True),          # case is not the user's problem
        ("nonsense", False),      # unknown value must not raise
        ("", False),
    ):
        at = run_app(mode=mode)
        check(
            f"?mode={mode!r} → {'observatory' if expect_admin else 'hot seat'}",
            not at.exception and is_admin(at) == expect_admin,
            str(at.exception)[:160],
        )


def test_toggle_round_trip() -> None:
    print("\nToggle")
    at = run_app()
    at.segmented_control[0].set_value("admin").run()
    check("toggling opens the observatory", is_admin(at), str(at.exception)[:160])
    check(
        "URL carries the slug, not the button label",
        url_mode(at) == "admin",
        repr(at.query_params.get("mode")),
    )
    at.segmented_control[0].set_value("founder").run()
    check("toggling back returns to the hot seat", not is_admin(at))
    check("URL follows back", url_mode(at) == "founder", repr(at.query_params.get("mode")))


def test_founder_isolation() -> None:
    print("\nHot Seat isolation")
    at = run_app(mode="founder", result=_result())
    check("hot seat renders a stored verdict", not at.exception, str(at.exception)[:160])
    text = page_text(at)

    # The whole point of the split. Each of these was on the founder's screen
    # before it, and each one breaks the illusion of facing a real board.
    for label, needle in (
        ("no Phoenix", "Phoenix"),
        ("no API key field", "API key"),
        ("no env var name", "ANTHROPIC_API_KEY"),
        ("no model id", "claude-"),
        ("no model picker", "Reasoning effort"),
        ("no seat selector", "Partner seats"),
        ("no evaluator", "Run evaluator"),
        ("no credit telemetry", "voucher"),
        ("no token footer", "tokens ("),
        ("no per-card token counts", " in / "),
        ("no reasoning drawer", THINKING),
        ("no trace span names", "roast.session"),
    ):
        check(label, needle not in text, f"leaked {needle!r}")

    # ...and the founder-facing surface is all still there.
    for label, needle in (
        ("term sheet rendered", "Non-binding term sheet"),
        ("scorecard rendered", "Delusion index"),
        ("pivot rendered", "Sell the telemetry to insurers."),
        ("mood dial present", "VC mood"),
        ("roster present", "The syndicate committee"),
    ):
        check(label, needle in text, f"missing {needle!r}")


def test_observatory_instruments() -> None:
    print("\nObservatory instruments")
    at = run_app(mode="admin", result=_result())
    check("observatory renders", not at.exception, str(at.exception)[:160])
    text = page_text(at)
    for label, needle in (
        ("Phoenix hub", "Arize Phoenix OSS hub"),
        ("trace tree", "roast.session"),
        ("credit telemetry", "voucher"),
        ("model orchestration", "Model orchestration"),
        ("concurrency panel", "Saved by fan-out"),
        ("deliberation inspector", THINKING),
        ("evaluator", "Run evaluator"),
        ("the same verdict", "Non-binding term sheet"),
        ("technical footer", "tokens ("),
    ):
        check(label, needle in text, f"missing {needle!r}")

    # The fan-out numbers must be the measured ones, not a guess: three seats
    # at 4.0 / 5.0 / 6.0s is 15.0s sequential against a 6.0s slowest seat.
    check("sequential equivalent is exact", "15.0s" in text)
    check("saved-by-fan-out is exact", "9.0s" in text)


def test_shared_state() -> None:
    print("\nShared session state")
    at = run_app(mode="founder", result=_result())
    at.segmented_control[0].set_value("admin").run()
    check("verdict survives the flip", not at.exception and is_admin(at))
    check(
        "and it is the same object, not a re-run",
        at.session_state["result"].session_id == "deadbeefdeadbeef",
    )
    check("no roast was billed by the flip", at.session_state["spend"] == [])

    # An operator setting chosen in the Observatory has to survive a trip
    # through the founder view, where its widget is not rendered at all.
    at.selectbox(key="cfg_model_label").set_value("Fable 5.1 — fast iteration").run()
    at.segmented_control[0].set_value("founder").run()
    check(
        "model choice survives a flip to the hot seat",
        at.session_state["cfg_model_label"] == "Fable 5.1 — fast iteration",
        repr(at.session_state.get("cfg_model_label")),
    )
    at.segmented_control[0].set_value("admin").run()
    check(
        "and is still selected on return",
        at.selectbox(key="cfg_model_label").value == "Fable 5.1 — fast iteration",
    )


def test_founder_flow() -> None:
    print("\nHot Seat flow")
    at = run_app(mode="founder")
    at.pills(key="preset_choice").set_value("🐾 Uber for Cats").run()
    check(
        "a quick pitch loads into the box",
        "emotional support cat" in at.text_area(key="pitch_text").value,
    )
    at.button(key="clear_btn").click().run()
    check("clear empties the box", at.text_area(key="pitch_text").value == "")

    # An empty pitch must be caught before anything is billed.
    at.button(key="convene_btn").click().run()
    check("empty pitch is refused", bool(at.warning), "no warning shown")
    check("nothing was billed", at.session_state["spend"] == [])


def test_state_guards() -> None:
    """Widget options are a browser-side convenience, not a wire guarantee.

    Exercised through a bare script rather than `app.py`: the accessors are the
    thing under test, and feeding an off-options value to a rendered widget
    trips AppTest's own selectbox helper before the app ever sees it.
    """
    print("\nState guards")

    at = AppTest.from_string(
        "import streamlit as st\n"
        "import state\n"
        "st.session_state['cfg_panel'] = ['marc', 'not-a-partner']\n"
        "st.session_state['cfg_effort'] = 'ludicrous'\n"
        "st.session_state['cfg_model_label'] = 'Nonexistent 9000'\n"
        "st.session_state['cfg_mood'] = 'whatever'\n"
        "st.write('panel=' + ','.join(state.panel()))\n"
        "st.write('effort=' + state.effort())\n"
        "st.write('model=' + state.model_id())\n"
        "st.write('brutality=%.2f' % state.brutality())\n",
        default_timeout=TIMEOUT,
    ).run()
    written = "\n".join(m.value for m in at.markdown)
    check("accessors survive hostile state", not at.exception, str(at.exception)[:160])
    # `convene` raises on an unknown partner id, so the filter is load-bearing.
    check("bogus seat ids are dropped", "panel=marc" in written, written)
    check("unknown effort falls back", f"effort={s.DEFAULT_EFFORT}" in written, written)
    check("unknown model falls back", f"model={s.DEFAULT_MODEL}" in written, written)
    check("unknown mood falls back", "brutality=0.85" in written, written)


def test_costs() -> None:
    print("\nCredit arithmetic")
    os.environ.pop("PITCHROAST_PRICING", None)
    os.environ["PITCHROAST_EUR_PER_USD"] = "1.0"
    os.environ["PITCHROAST_VOUCHER_EUR"] = "100"

    check(
        "published rate is used",
        costs.usd_of("claude-opus-5", 1_000_000, 1_000_000) == 30.0,
    )
    check("published rate is marked confirmed", costs.price_for("claude-opus-5").confirmed)
    check(
        "an unlisted model is charged at the Opus tier, flagged",
        costs.price_for("claude-opus-5-5") == costs.ASSUMED
        and not costs.price_for("claude-opus-5-5").confirmed,
    )

    os.environ["PITCHROAST_PRICING"] = '{"claude-opus-5-5": [4, 20]}'
    check(
        "an override replaces the guess",
        costs.usd_of("claude-opus-5-5", 1_000_000, 0) == 4.0
        and costs.price_for("claude-opus-5-5").confirmed,
    )
    os.environ["PITCHROAST_PRICING"] = "{not json"
    check(
        "a broken override is ignored rather than fatal",
        costs.price_for("claude-opus-5-5") == costs.ASSUMED,
    )
    os.environ.pop("PITCHROAST_PRICING")

    run = costs.cost_of(_result())
    check("a run is costed from its own token counts", run.total_tokens == 6000)
    check(
        "at the model's rate",
        abs(run.usd - costs.usd_of("claude-opus-5-5", 4000, 2000)) < 1e-12,
    )
    check("and inherits the confirmed flag", not run.confirmed)

    totals = costs.totals([run, run])
    check("totals add up", totals.runs == 2 and totals.total_tokens == 12000)
    check("totals flag assumed prices", totals.assumed_prices)
    check("a partial voucher reads as a fraction", 0.0 < totals.voucher_used < 1.0)

    big = costs.totals([costs.RunCost("m", 0, 0, 10_000.0, 1.0, 3, "x", True)])
    check("voucher progress clamps at 1.0", big.voucher_used == 1.0)
    check("and the remainder never goes negative", big.voucher_left_eur == 0.0)

    os.environ["PITCHROAST_EUR_PER_USD"] = "-3"
    check("a nonsense FX rate falls back to the default", costs.eur_per_usd() == costs.DEFAULT_EUR_PER_USD)
    os.environ["PITCHROAST_EUR_PER_USD"] = "1.0"
    check("a sub-cent roast is not rendered as €0.00", costs.eur(0.0004) == "€0.0004")


def main() -> int:
    # Belt and braces: none of this should reach the network, but a stray key
    # in the environment plus a bug in the run guard is a real way to spend
    # money from a test suite.
    os.environ.pop("ANTHROPIC_API_KEY", None)

    # `app.py` boots Phoenix in both modes. Launching a real server (and binding
    # a port that may already be in use on a demo machine) is not this suite's
    # job, so hand the bootstrap a disabled handle. The Observatory renders its
    # "tracing off" path, which is worth covering anyway.
    obs.setup_observability = lambda project=None: obs.Tracing(  # type: ignore[assignment]
        project="pitchroast-test", detail="stubbed by test_modes.py"
    )

    test_routing()
    test_toggle_round_trip()
    test_founder_isolation()
    test_observatory_instruments()
    test_shared_state()
    test_founder_flow()
    test_state_guards()
    test_costs()

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} check(s) failed: {', '.join(FAILURES)}\n")
        return 1
    print("✅ All mode checks passed (no API calls, no Phoenix, no key needed).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
