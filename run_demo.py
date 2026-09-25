#!/usr/bin/env python3
"""
PitchRoast 🔥 — Headless Syndicate Runner
=========================================

Drives the full four-agent investment committee from the terminal via
``syndicate.convene()``. This is both the stage fallback (if the Streamlit UI
stalls, this is the same demo without the CSS) and the ``make demo`` smoke test.

All prompting, schema enforcement, parallelism and tracing live in
``syndicate.py`` — this file is presentation and process control only.

Exit codes
----------
0   verdict rendered successfully
1   runtime failure, committee refusal, or I/O error
2   bad command-line arguments
130 interrupted (Ctrl-C)
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import os
import sys
import textwrap
import time
from typing import Any

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
    term_sheet_text,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INTERRUPT = 130

API_BASE = "https://api.anthropic.com"
RULE = "=" * 80
WRAP = 78

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# Verbatim from app.py's preset_options — keep these in sync with the UI.
PRESETS: dict[str, tuple[str, str]] = {
    "oatmilk": (
        "☕ Autonomous Oat Milk Micro-Roastery with Web3 Proof-of-Foam",
        (
            "A decentralized network of countertop espresso machines that roast "
            "small-batch Nordic oat milk using on-chain temperature consensus. "
            "Users stake OAT tokens for latte art NFTs. Market size: $400B "
            "addressable beverage space."
        ),
    ),
    "proxy": (
        "🤖 AI Meeting Proxy that says 'Blocked by Backend' in 14 accents",
        (
            "An autonomous AI agent avatar that joins daily Scrum standups on "
            "Zoom/Teams, randomly sighs, checks its phone, and responds 'I am "
            "blocked by the infrastructure backend' whenever your name is called. "
            "B2B SaaS priced at $49/engineer/month."
        ),
    ),
    "cats": (
        "🐾 Uber for Cats: Feline Scooter On-Demand",
        (
            "High-density urban cat affection. When an office worker feels burnt "
            "out, our app dispatches an autonomous electric scooter carrying a "
            "pre-vetted emotional support cat to their office lobby for a "
            "15-minute petting session."
        ),
    ),
    "pizza": (
        "🍕 Tinder for Leftover Pizza: Peer-to-Peer Slice Swapping",
        (
            "A location-based peer-to-peer marketplace where college students "
            "swipe right on half-eaten pizza slices in nearby dorm rooms. Powered "
            "by zero-knowledge crust verification."
        ),
    ),
}
DEFAULT_PRESET = "oatmilk"

# --------------------------------------------------------------------------- #
# Output plumbing — in --json mode every human-readable line goes to stderr so
# stdout stays a clean JSON document.
# --------------------------------------------------------------------------- #

_OUT = sys.stdout


def log(message: str = "") -> None:
    print(message, file=_OUT, flush=True)


def banner(title: str) -> None:
    log()
    log(RULE)
    log(title)
    log(RULE)


def wrap(text: str, indent: str = "  ", first: str | None = None) -> str:
    return textwrap.fill(
        " ".join(str(text).split()),
        width=WRAP,
        initial_indent=first if first is not None else indent,
        subsequent_indent=indent,
    )


def glyph(partner: Partner) -> str:
    """Terminal icon for a partner.

    ``Partner.icon`` is a Material Symbols name for the Streamlit UI
    ("trending_down"), which is meaningless in a terminal; ``Partner.emoji`` is
    the one that renders. Fall back gracefully if either is absent.
    """
    return getattr(partner, "emoji", "") or "•"


def key_prefix(key: str) -> str:
    """Projector-safe key rendering: a short prefix and nothing else.

    Never print the tail — the trailing characters are the high-entropy part.
    """
    return f"{key[:8]}…" if len(key) > 8 else "…"


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    preset_help = "\n".join(f"  {name:<9} {label}" for name, (label, _) in PRESETS.items())
    model_help = "\n".join(f"  {mid:<20} {label}" for label, mid in MODELS.items())

    parser = argparse.ArgumentParser(
        prog="run_demo.py",
        description="Convene the PitchRoast autonomous venture committee from the CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"presets:\n{preset_help}\n\nmodels:\n{model_help}\n",
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--pitch",
        metavar="TEXT",
        help="Free-text startup pitch to put in front of the committee.",
    )
    source.add_argument(
        "--preset",
        metavar="NAME",
        choices=tuple(PRESETS),
        default=DEFAULT_PRESET,
        help=f"Use a built-in pitch (default: {DEFAULT_PRESET}).",
    )

    parser.add_argument(
        "--model",
        metavar="ID",
        default=DEFAULT_MODEL,
        help=f"Model ID to convene with (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--brutality",
        metavar="FLOAT",
        type=float,
        default=0.85,
        help="Brutality index, 0.0-1.0 (default: 0.85).",
    )
    parser.add_argument(
        "--effort",
        choices=EFFORT_LEVELS,
        default="medium",
        help="Reasoning effort passed to output_config (default: medium).",
    )
    parser.add_argument(
        "--no-phoenix",
        dest="no_phoenix",
        action="store_true",
        help="Skip Arize Phoenix startup (faster boot, no traces).",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the raw result as JSON on stdout instead of the pretty report.",
    )
    parser.add_argument(
        "--save",
        metavar="PATH",
        help="Write the term sheet text to PATH.",
    )
    return parser


def resolve_args(parser: argparse.ArgumentParser, argv: list[str] | None) -> argparse.Namespace:
    """Parse and validate. Any rejection exits with code 2 via parser.error()."""
    args = parser.parse_args(argv)

    valid_models = tuple(MODELS.values())
    if args.model not in valid_models:
        parser.error(f"unknown --model {args.model!r}; choose one of: {', '.join(valid_models)}")

    if not 0.0 <= args.brutality <= 1.0:
        parser.error(f"--brutality must be between 0.0 and 1.0 (got {args.brutality})")

    if args.pitch is not None:
        pitch = " ".join(args.pitch.split())
        if not pitch:
            parser.error("--pitch must not be empty")
        args.pitch_text = pitch
        args.pitch_label = "custom pitch"
    else:
        label, text = PRESETS[args.preset]
        args.pitch_text = text
        args.pitch_label = label

    return args


# --------------------------------------------------------------------------- #
# JSON serialisation
# --------------------------------------------------------------------------- #


def to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / pydantic models into JSON-safe data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):  # pydantic v2 models
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    return str(obj)


def result_payload(result: SyndicateResult, phoenix_url: str | None) -> dict[str, Any]:
    payload = to_jsonable(result)
    if not isinstance(payload, dict):  # defensive; SyndicateResult is a dataclass
        payload = {"result": payload}
    payload["total_tokens"] = result.total_tokens
    payload["ok"] = result.ok
    payload["phoenix_url"] = phoenix_url
    return payload


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def ordered_partners(results: list[PartnerResult]) -> list[PartnerResult]:
    """Render in the canonical PARTNERS order regardless of completion order."""
    rank = {p.id: i for i, p in enumerate(PARTNERS)}
    return sorted(results, key=lambda r: rank.get(r.partner.id, len(rank)))


def render_header(args: argparse.Namespace, api_key: str) -> None:
    label = next((lbl for lbl, mid in MODELS.items() if mid == args.model), args.model)
    banner("🔥 PITCHROAST — THE AUTONOMOUS VENTURE COMMITTEE")
    log(f"  🔑 Key         {key_prefix(api_key)}")
    log(f"  🌐 Endpoint    {API_BASE}")
    log(f"  🧠 Model       {args.model}  ({label})")
    log(f"  🎚️  Brutality   {args.brutality:.2f}        Effort  {args.effort}")
    log(f"  👥 Committee   {len(PARTNERS)} partners + {SHARK.name}")


def render_pitch(args: argparse.Namespace) -> None:
    banner("📋 SUBMITTED STARTUP PITCH")
    log(f"  {args.pitch_label}")
    log()
    log(wrap(args.pitch_text, indent="  ", first="  👉 "))


def render_scorecard(result: SyndicateResult) -> None:
    shark = result.shark
    if shark is None:
        return
    banner("📊 SYNDICATE QUANTITATIVE SCORECARD")
    log(f"  • Delusion Index        {shark.delusion_index:>3} / 100")
    log(f"  • True Moat Score       {shark.moat_score:>3} / 10")
    log(f"  • Projected Runway      {shark.runway_months:>3} months")
    log(f"  • Pre-Money Valuation   {shark.pre_money_val}")


def render_debate(result: SyndicateResult) -> None:
    banner("🎙️  THE BOARDROOM DEBATE")
    for res in ordered_partners(result.partners):
        partner = res.partner
        log()
        log(f"{glyph(partner)} [{partner.name.upper()} | {partner.title}]")
        log(f"   focus: {partner.focus}")
        log("-" * WRAP)
        if res.recused or res.verdict is None:
            log(f"  🚫 RECUSED — {res.error or 'no verdict returned'}")
            log("     (the committee proceeded without this seat)")
            continue
        verdict = res.verdict
        log(wrap(verdict.critique))
        log()
        log(wrap(f'"{verdict.zinger}"', indent="     ", first="  💬 "))
        log(
            f"  📈 delusion {verdict.delusion_index}/100 · "
            f"moat {verdict.moat_score}/10 · "
            f"runway {verdict.runway_months}mo · "
            f"{res.latency_s:.1f}s"
        )


def render_deliberation(result: SyndicateResult) -> None:
    thinking = (result.shark_thinking or "").strip()
    if not thinking:
        return
    banner("🧠 SHARK DELIBERATION (summarized reasoning)")
    for line in thinking.splitlines():
        log(wrap(line) if line.strip() else "")


def render_term_sheet(result: SyndicateResult) -> None:
    shark = result.shark
    if shark is None:
        return
    sheet = shark.term_sheet
    banner("📜 OFFICIAL SYNDICATE TERM SHEET")
    log(f"  • VALUATION          {sheet.valuation}")
    log(f"  • INVESTMENT         {sheet.investment_amount}")
    log(f"  • LIQUIDATION PREF   {sheet.liquidation_pref}")
    log("  • MANDATORY FOUNDER COVENANTS:")
    for idx, covenant in enumerate(sheet.covenants, start=1):
        log(wrap(covenant, indent="          ", first=f"     [{idx}] "))


def render_pivot_and_verdict(result: SyndicateResult) -> None:
    shark = result.shark
    if shark is None:
        return
    banner("💡 THE 1% PIVOT — the part that could actually work")
    log(wrap(shark.the_pivot, indent="     ", first="  👉 "))

    banner(f"{glyph(SHARK)} FINAL VERDICT")
    log("  " + ("✅  FUNDED BY SYNDICATE" if shark.funded else "❌  REJECTED BY SYNDICATE"))
    log()
    log(wrap(shark.closing_line, indent="     ", first=f"  {glyph(SHARK)} "))


def render_telemetry(result: SyndicateResult, phoenix_url: str | None) -> None:
    banner("⚡ SESSION TELEMETRY & OBSERVABILITY")
    log(f"  {'AGENT':<26}{'IN':>9}{'OUT':>9}{'LATENCY':>10}   STATUS")
    log("  " + "-" * (WRAP - 2))

    partner_in = partner_out = 0
    for res in ordered_partners(result.partners):
        partner_in += res.input_tokens
        partner_out += res.output_tokens
        if res.recused or res.verdict is None:
            status = "recused"
        elif res.error:
            status = "error"
        else:
            status = "ok"
        # No icons in this table: emoji are not one column wide, so they break
        # the alignment on a projector.
        log(
            f"  {res.partner.name:<26}{res.input_tokens:>9}{res.output_tokens:>9}"
            f"{res.latency_s:>9.1f}s   {status}"
        )

    # SyndicateResult exposes only session totals, so the shark's own usage is
    # whatever the partners did not account for.
    log(
        f"  {SHARK.name:<26}{max(0, result.input_tokens - partner_in):>9}"
        f"{max(0, result.output_tokens - partner_out):>9}{'—':>10}   "
        f"{'ok' if result.shark is not None else 'missing'} (derived)"
    )

    log("  " + "-" * (WRAP - 2))
    log(
        f"  {'TOTAL':<26}{result.input_tokens:>9}{result.output_tokens:>9}"
        f"{result.latency_s:>9.1f}s   {result.total_tokens} tokens"
    )
    log()
    log(f"  • Model:         {result.model}")
    log(f"  • Wall clock:    {result.latency_s:.2f}s")
    log(f"  • Arize Phoenix: {phoenix_url or 'offline (no traces recorded)'}")


def render_report(result: SyndicateResult, phoenix_url: str | None) -> None:
    render_scorecard(result)
    render_debate(result)
    render_deliberation(result)
    render_term_sheet(result)
    render_pivot_and_verdict(result)
    render_telemetry(result, phoenix_url)
    log(RULE)
    log("✅ DEMO COMPLETED SUCCESSFULLY")
    log(RULE)
    log()


def render_refusal(result: SyndicateResult) -> None:
    banner("🚪 THE COMMITTEE HAS DECLINED TO TAKE THIS MEETING")
    log(wrap(result.refusal_reason or "The syndicate declined to review this pitch."))
    log()
    log("  No verdict, no scorecard, no term sheet. Try a different pitch.")
    log(RULE)


def render_failure(result: SyndicateResult) -> None:
    banner("❌ SYNDICATE SESSION FAILED")
    log(wrap(result.error or "The shark returned no verdict."))
    log()
    log("  Check the API key, remaining credits, and model availability")
    log("  (run `make test` for a typed connectivity diagnosis).")
    if result.partners:
        log()
        log("  Partial partner results:")
        for res in ordered_partners(result.partners):
            state = "recused" if res.recused else ("error" if res.error else "ok")
            log(f"    • {res.partner.name:<22} {state}")
    log(RULE)


# --------------------------------------------------------------------------- #
# Session plumbing
# --------------------------------------------------------------------------- #


def observability_starter():
    """Return a callable that boots tracing and yields ``(url, detail)``.

    ``setup_observability()`` is exported by ``syndicate``, but it also ships in
    a standalone ``observability`` module. Accept whichever is present, and
    normalise the return value — a URL string, or a Tracing-like object — down
    to a URL.
    """
    for module_name in ("syndicate", "observability"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        setup = getattr(module, "setup_observability", None)
        if setup is None:
            continue

        def start(setup=setup, module=module) -> tuple[str | None, str]:
            handle = setup()
            if handle is None:
                return None, ""
            if isinstance(handle, str):
                return handle, ""
            deep_link = getattr(module, "trace_url", None)
            url = (deep_link(handle) if deep_link else None) or getattr(handle, "url", None)
            return url, getattr(handle, "detail", "") or ""

        return start
    return None


def start_phoenix(enabled: bool) -> str | None:
    if not enabled:
        log("\n🔭 Phoenix observability skipped (--no-phoenix).")
        return None

    starter = observability_starter()
    if starter is None:
        log("\n🔭 Phoenix observability unavailable — no setup_observability() found.")
        return None

    log("\n🔭 Booting Arize Phoenix OSS observability…")
    try:
        url, detail = starter()
    except Exception as exc:  # noqa: BLE001 — tracing is never allowed to kill the demo
        log(f"⚠️  Phoenix unavailable: {type(exc).__name__}: {exc}")
        return None
    if url:
        log(f"✅ Tracing live at {url}")
    else:
        log(f"⚠️  Tracing offline — spans will not be recorded. {detail}".rstrip())
    return url


def make_progress_printer(started: float):
    """Print each agent as it lands, so the terminal shows the parallelism."""

    def on_event(event: Event) -> None:
        stamp = f"[{time.perf_counter() - started:5.1f}s]"
        partner = event.partner or (event.result.partner if event.result else None)
        who = f"{glyph(partner)} {partner.name}" if partner else "committee"

        if event.kind == "partner_start":
            log(f"{stamp} ⏳ {who} — dispatched")
        elif event.kind == "partner_done":
            res = event.result
            if res is None:
                log(f"{stamp} ✅ {who} — returned")
            elif res.recused or res.verdict is None:
                log(f"{stamp} 🚫 {who} — RECUSED ({res.error or 'no verdict'})")
            elif res.error:
                log(f"{stamp} ❌ {who} — {res.error}")
            else:
                log(f"{stamp} ✅ {who} — {res.latency_s:.1f}s, {res.output_tokens} out tok")
        elif event.kind == "shark_start":
            log(f"{stamp} {glyph(SHARK)} {SHARK.name} is reading the room…")
        elif event.kind == "shark_done":
            log(f"{stamp} {glyph(SHARK)} {SHARK.name} — verdict in")

    return on_event


def save_term_sheet(path: str, result: SyndicateResult) -> bool:
    if result.shark is None:
        log(f"\n⚠️  Nothing to save to {path} — no term sheet was issued.")
        return False
    try:
        text = term_sheet_text(result)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text if text.endswith("\n") else text + "\n")
    except OSError as exc:
        log(f"\n❌ Could not write term sheet to {path}: {exc}")
        return False
    log(f"\n💾 Term sheet written to {path}")
    return True


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    global _OUT

    parser = build_parser()
    args = resolve_args(parser, argv)

    if args.as_json:
        # stdout is reserved for the JSON document.
        _OUT = sys.stderr

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log("❌ ANTHROPIC_API_KEY is not set.")
        log("   Run ./set_key.sh sk-ant-... or export the variable, then retry.")
        return EXIT_FAIL

    render_header(args, api_key)
    phoenix_url = start_phoenix(not args.no_phoenix)
    render_pitch(args)

    banner("⚡ CONVENING THE SYNDICATE")
    started = time.perf_counter()
    try:
        result = convene(
            args.pitch_text,
            api_key=api_key,
            model=args.model,
            brutality=args.brutality,
            effort=args.effort,
            on_event=make_progress_printer(started),
        )
    except SyndicateError as exc:
        log(f"\n❌ Syndicate failed: {exc}")
        return EXIT_FAIL
    except KeyboardInterrupt:
        log("\n🛑 Interrupted before the committee reported back.")
        return EXIT_INTERRUPT
    except Exception as exc:  # noqa: BLE001 — `make demo` must exit 1, never traceback
        log(f"\n❌ Unexpected failure: {type(exc).__name__}: {exc}")
        return EXIT_FAIL

    failed = bool(result.refused or result.error or result.shark is None)
    status = EXIT_FAIL if failed else EXIT_OK

    if args.as_json:
        json.dump(result_payload(result, phoenix_url), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        if result.refused:
            log("\n🚪 Committee refused — see refusal_reason in the JSON payload.")
        elif failed:
            log("\n❌ Session failed — see error in the JSON payload.")
    elif result.refused:
        render_refusal(result)
    elif failed:
        render_failure(result)
    else:
        render_report(result, phoenix_url)

    if args.save and not save_term_sheet(args.save, result):
        status = EXIT_FAIL

    return status


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🛑 Aborted.", file=sys.stderr)
        sys.exit(EXIT_INTERRUPT)
