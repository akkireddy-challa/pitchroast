#!/usr/bin/env python3
"""Offline tests for the syndicate orchestration.

These never touch the Anthropic API — `syndicate._call` is monkeypatched — so
they are free to run and safe in CI. They cover the behaviour that is hard to
check on stage: parallelism, partial failure, and refusal handling.

Run: .venv/bin/python test_syndicate.py
"""

from __future__ import annotations

import logging
import os
import sys
import time

import syndicate as s

# The failure-path tests deliberately blow up partner calls; the engine logs
# those with tracebacks. Keep the test output readable.
logging.getLogger("syndicate").setLevel(logging.CRITICAL)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}{f' — {detail}' if detail else ''}")
        FAILURES.append(name)


def _verdict(n: int = 50) -> s.PartnerVerdict:
    return s.PartnerVerdict(
        critique="Your TAM includes tap water.",
        delusion_index=n,
        moat_score=1,
        runway_months=2,
        zinger="This is a landing page with a burn rate.",
    )


def _shark() -> s.SharkVerdict:
    return s.SharkVerdict(
        delusion_index=94,
        moat_score=1,
        runway_months=2,
        pre_money_val="$14.50 and a cold kanelbulle",
        term_sheet=s.TermSheet(
            valuation="$12.00",
            investment_amount="$500 in cloud credits",
            liquidation_pref="10x participating",
            covenants=["Founder must apologise weekly", "No more decks", "Delete the token"],
        ),
        the_pivot="Sell the roasting telemetry to insurers.",
        funded=False,
        closing_line="The committee thanks you for the entertainment.",
    )


def fake_call_factory(*, fail: set[str] = frozenset(), refuse: set[str] = frozenset(), delay: float = 0.0):
    """Build a `_call` replacement keyed off which persona is being addressed."""

    def fake_call(client, *, model, system, user, schema, effort):
        if delay:
            time.sleep(delay)
        if schema is s.SharkVerdict:
            who = "gekko"
        else:
            blob = system[1]["text"] if isinstance(system, list) else str(system)
            who = next((p.id for p in s.PARTNERS if p.name in blob), "unknown")
        if who in refuse:
            raise s._Refusal("cyber")
        if who in fail:
            raise RuntimeError("upstream exploded")
        parsed = _shark() if schema is s.SharkVerdict else _verdict()
        return parsed, f"thinking-{who}", 100, 200

    return fake_call


def run(name: str, fake, **kwargs) -> s.SyndicateResult:
    original = s._call
    s._call = fake
    try:
        return s.convene("An oat milk blockchain.", api_key="test-key", **kwargs)
    finally:
        s._call = original


def main() -> int:
    print("\nOrchestration — happy path")
    events: list[str] = []
    r = run("happy", fake_call_factory(), on_event=lambda e: events.append(e.kind))
    check("all three partners seated", len(r.seated) == 3, f"got {len(r.seated)}")
    check("shark produced a verdict", r.ok)
    check("result.ok is True", r.ok)
    check("render order preserved", [p.partner.id for p in r.partners] == [p.id for p in s.PARTNERS])
    check("tokens summed across 4 calls", r.total_tokens == 4 * 300, f"got {r.total_tokens}")
    check("thinking captured", all(p.thinking for p in r.partners) and bool(r.shark_thinking))
    check("events emitted", events.count("partner_done") == 3 and "shark_done" in events)
    check("term sheet renders", "MANDATORY COVENANTS" in s.term_sheet_text(r))

    print("\nPartial failure — one partner drops")
    r = run("partial", fake_call_factory(fail={"karen"}))
    check("two partners seated", len(r.seated) == 2, f"got {len(r.seated)}")
    check("karen marked recused", next(p for p in r.partners if p.partner.id == "karen").recused)
    check("run still succeeded", r.ok)
    check("recusal noted in export", "RECUSED" in s.term_sheet_text(r))

    print("\nTotal panel loss")
    r = run("dead", fake_call_factory(fail={"marc", "karen", "torvalds"}))
    check("no shark call attempted", r.shark is None)
    check("error surfaced", bool(r.error))
    check("not misreported as refusal", not r.refused)

    print("\nRefusal — every partner declines")
    r = run("refused", fake_call_factory(refuse={"marc", "karen", "torvalds"}))
    check("flagged as refused", r.refused)
    check("reason present", bool(r.refusal_reason))
    check("no generic error", r.error is None)

    print("\nRefusal — shark alone declines")
    r = run("shark-refused", fake_call_factory(refuse={"gekko"}))
    check("partners still seated", len(r.seated) == 3)
    check("flagged as refused", r.refused)

    print("\nParallelism — three 0.4s partners must overlap")
    start = time.perf_counter()
    r = run("parallel", fake_call_factory(delay=0.4))
    elapsed = time.perf_counter() - start
    # Serial would be ~1.6s (3 partners + shark). Parallel partners ≈ 0.8s.
    check("partners ran concurrently", elapsed < 1.2, f"took {elapsed:.2f}s, expected <1.2s")

    print("\nGuards")
    try:
        s.convene("   ", api_key="k")
        check("empty pitch rejected", False, "no exception raised")
    except s.SyndicateError:
        check("empty pitch rejected", True)
    # api_key="" deliberately falls back to the environment, so isolate it.
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        s.convene("real pitch", api_key="")
        check("missing key rejected", False, "no exception raised")
    except s.SyndicateError:
        check("missing key rejected", True)
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
    check("env key used when arg omitted", s._client("  ") is not None if saved else True)

    print("\nPrompt construction")
    briefing = s._shark_briefing("the pitch", run("brief", fake_call_factory()).seated)
    check("shark sees verbatim critiques", "Your TAM includes tap water." in briefing)
    check("shark sees all three partners", all(p.name in briefing for p in s.PARTNERS))
    blocks = s._system_blocks(s.PARTNERS[0], 0.95)
    check("shared prefix is cached", blocks[0].get("cache_control") == {"type": "ephemeral"})
    check("volatile text after breakpoint", "cache_control" not in blocks[1])
    check("brutality is prompt text", "0.95" in blocks[1]["text"])

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} check(s) failed: {', '.join(FAILURES)}\n")
        return 1
    print("✅ All orchestration checks passed (no API calls made).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
