#!/usr/bin/env python3
"""
PitchRoast 🔥 — Anthropic API connectivity probe
================================================

Verifies that the event key works and that every model PitchRoast can select is
actually reachable. Run by ``make test`` and by ``set_key.sh``.

Valid model IDs (verified against the live ``GET /v1/models`` with the event key
on 2026-09-25 — all three are real and provisioned):

    claude-opus-5-5     🧠 stage demo, newest
    claude-fable-5-1    ⚡ fast iteration
    claude-opus-5       🏛️ classic frontier fallback

The probe does three things, in order:

1. Lists the model catalog the key can see (free, no tokens) — the fastest way
   to catch an ID that has been renamed or deprovisioned before it fails on stage.
2. Sends one trivial ``max_tokens=16`` request per model and reports latency and
   token usage.
3. Distinguishes the failure modes by type — "is my key bad" and "is that model
   real" have different fixes.

Exit codes
----------
0   every probed model answered
1   at least one probe failed, or no API key
2   bad command-line arguments
130 interrupted (Ctrl-C)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

from syndicate import DEFAULT_MODEL, MODELS

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INTERRUPT = 130

API_BASE = "https://api.anthropic.com"
RULE = "=" * 80
THIN = "-" * 80

PROBE_PROMPT = "Reply with the single word: OK"
PROBE_MAX_TOKENS = 16


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def key_prefix(key: str) -> str:
    """Projector-safe key rendering: a short prefix, never the tail."""
    return f"{key[:8]}…" if len(key) > 8 else "…"


def api_message(exc: Exception, limit: int = 220) -> str:
    """The server's own message, flattened to one line."""
    raw = getattr(exc, "message", None) or str(exc)
    flat = " ".join(str(raw).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


@dataclass
class ProbeOutcome:
    model_id: str
    display_name: str
    ok: bool
    latency_s: float
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None
    reply: str = ""
    notes: list[str] = field(default_factory=list)
    failure: str = ""
    detail: str = ""
    hint: str = ""


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #


def fetch_catalog(client: anthropic.Anthropic) -> tuple[dict[str, str], str | None]:
    """Return ``{model_id: display_name}`` for everything this key can see.

    Free call — no tokens spent. Returns an error string instead of raising.
    """
    catalog: dict[str, str] = {}
    try:
        for info in client.models.list(limit=100):
            catalog[info.id] = info.display_name
    except anthropic.AuthenticationError as exc:
        return catalog, f"AuthenticationError (HTTP 401) — the key was rejected: {api_message(exc)}"
    except anthropic.PermissionDeniedError as exc:
        return catalog, f"PermissionDeniedError (HTTP 403) — key lacks access: {api_message(exc)}"
    except anthropic.APIConnectionError as exc:
        return catalog, f"APIConnectionError — could not reach {API_BASE}: {api_message(exc)}"
    except anthropic.APIStatusError as exc:
        return catalog, f"APIStatusError (HTTP {exc.status_code}) — {api_message(exc)}"
    except anthropic.AnthropicError as exc:
        return catalog, f"{type(exc).__name__} — {api_message(exc)}"
    return catalog, None


def render_catalog(catalog: dict[str, str], error: str | None, targets: list[str]) -> None:
    print()
    print(THIN)
    print("📚 MODEL CATALOG VISIBLE TO THIS KEY  (GET /v1/models — free)")
    print(THIN)

    if error:
        print(f"  ⚠️  Catalog unavailable: {error}")
        print("     Continuing to the live probes — they will confirm the diagnosis.")
        return

    if not catalog:
        print("  ⚠️  The key can see zero models. That is almost certainly a")
        print("     provisioning problem, not a code problem.")
        return

    configured = set(MODELS.values())
    for model_id, display_name in catalog.items():
        marks = []
        if model_id in configured:
            marks.append("PitchRoast")
        if model_id == DEFAULT_MODEL:
            marks.append("default")
        if model_id in targets:
            marks.append("probing")
        tag = f"  ← {', '.join(marks)}" if marks else ""
        print(f"  • {model_id:<22} {display_name:<26}{tag}")

    missing = [m for m in targets if m not in catalog]
    if missing:
        print()
        print("  ⚠️  Requested but NOT in the catalog — expect NotFoundError:")
        for model_id in missing:
            print(f"     ❌ {model_id}")
        print("     The ID was renamed or deprovisioned. Fix it in syndicate.MODELS.")


# --------------------------------------------------------------------------- #
# Probe
# --------------------------------------------------------------------------- #


def probe(client: anthropic.Anthropic, model_id: str, display_name: str) -> ProbeOutcome:
    """One trivial request. The typed except chain is the whole point."""
    started = time.perf_counter()
    diagnosis: tuple[str, str, str, Exception] | None = None

    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=PROBE_MAX_TOKENS,
            messages=[{"role": "user", "content": PROBE_PROMPT}],
        )
    except anthropic.AuthenticationError as exc:
        diagnosis = (
            "AuthenticationError (HTTP 401)",
            "The key itself was rejected — this is not about the model.",
            "Key is wrong, revoked, or from another org. Re-run ./set_key.sh with a fresh key.",
            exc,
        )
    except anthropic.PermissionDeniedError as exc:
        diagnosis = (
            "PermissionDeniedError (HTTP 403)",
            "The key is valid but not allowed to use this model.",
            "Ask for entitlement in the Console, or pick a model the catalog above lists.",
            exc,
        )
    except anthropic.NotFoundError as exc:
        diagnosis = (
            "NotFoundError (HTTP 404)",
            "The model ID does not exist for this key — the key is fine.",
            f"{model_id!r} is misspelled, renamed, or deprovisioned. Compare it to the catalog above.",
            exc,
        )
    except anthropic.RateLimitError as exc:
        retry_after = "unknown"
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            retry_after = response_obj.headers.get("retry-after", "unknown")
        diagnosis = (
            "RateLimitError (HTTP 429)",
            f"Key and model are both fine — you are being throttled (retry-after: {retry_after}s).",
            "Wait and retry, or fall back 5.5 → 5 → Fable 5.1 on stage.",
            exc,
        )
    except anthropic.BadRequestError as exc:
        diagnosis = (
            "BadRequestError (HTTP 400)",
            "The request shape is invalid for this model (an unsupported parameter).",
            "No temperature/top_p/top_k and no budget_tokens on these models — see BUILD_SPEC §4.2.",
            exc,
        )
    except anthropic.APITimeoutError as exc:
        diagnosis = (
            "APITimeoutError",
            "The request was sent but no response arrived in time.",
            "Venue network or a slow model. Retry; on stage prefer the pre-warmed transcript.",
            exc,
        )
    except anthropic.APIConnectionError as exc:
        diagnosis = (
            "APIConnectionError",
            f"Never reached {API_BASE} — DNS, TLS, proxy, or no network.",
            "Check the connection/proxy. Note PitchRoast deliberately bypasses Telia LiteLLM.",
            exc,
        )
    except anthropic.APIStatusError as exc:
        diagnosis = (
            f"APIStatusError (HTTP {exc.status_code})",
            "The API returned an error status that is none of the specific cases above.",
            "5xx is transient — retry. 4xx means the request needs changing.",
            exc,
        )
    except anthropic.AnthropicError as exc:
        diagnosis = (
            type(exc).__name__,
            "SDK-level failure before or after the HTTP exchange.",
            "Usually a client/credential configuration problem rather than the API.",
            exc,
        )

    latency = time.perf_counter() - started

    if diagnosis is not None:
        failure, detail, hint, exc = diagnosis
        return ProbeOutcome(
            model_id=model_id,
            display_name=display_name,
            ok=False,
            latency_s=latency,
            failure=failure,
            detail=detail,
            hint=hint,
            notes=[f"api says: {api_message(exc)}"],
        )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    notes: list[str] = []
    if response.stop_reason == "max_tokens":
        notes.append(
            f"truncated at max_tokens={PROBE_MAX_TOKENS} — expected on a thinking model, "
            "connectivity is still confirmed"
        )
    elif response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None)
        notes.append(f"the model declined the probe (category: {category}) — transport is fine")

    return ProbeOutcome(
        model_id=model_id,
        # The live catalog is authoritative; fall back to what the API served.
        display_name=display_name or getattr(response, "model", model_id),
        ok=True,
        latency_s=latency,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason,
        reply=text,
        notes=notes,
    )


def render_outcome(outcome: ProbeOutcome) -> None:
    print()
    if outcome.ok:
        print(
            f"  ✅ {outcome.model_id:<22} {outcome.display_name:<26}"
            f"{outcome.latency_s:>7.2f}s"
        )
        print(
            f"     ↳ tokens: in {outcome.input_tokens} / out {outcome.output_tokens}"
            f"   ·   stop_reason: {outcome.stop_reason}"
        )
        if outcome.reply:
            print(f'     ↳ reply: "{outcome.reply}"')
    else:
        print(
            f"  ❌ {outcome.model_id:<22} {outcome.display_name:<26}"
            f"{outcome.latency_s:>7.2f}s"
        )
        print(f"     ↳ {outcome.failure}: {outcome.detail}")
        print(f"     ↳ fix: {outcome.hint}")
    for note in outcome.notes:
        print(f"     ↳ {note}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    catalog_help = "\n".join(f"  {mid:<20} {label}" for label, mid in MODELS.items())
    parser = argparse.ArgumentParser(
        prog="test_connection.py",
        description="Probe the Anthropic API key against every model PitchRoast can select.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"configured models:\n{catalog_help}\n",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--model",
        metavar="ID",
        help="Probe one model ID only (any ID — unknown IDs are probed on purpose).",
    )
    scope.add_argument(
        "--quick",
        action="store_true",
        help=f"Probe only the default model ({DEFAULT_MODEL}).",
    )
    return parser


def select_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Return ``[(model_id, label)]`` to probe."""
    by_id = {model_id: label for label, model_id in MODELS.items()}
    if args.model:
        return [(args.model, by_id.get(args.model, "(not in syndicate.MODELS)"))]
    if args.quick:
        return [(DEFAULT_MODEL, by_id.get(DEFAULT_MODEL, "(not in syndicate.MODELS)"))]
    return [(model_id, label) for label, model_id in MODELS.items()]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY is not set.")
        print("   Set it with one of:")
        print("     ./set_key.sh sk-ant-...")
        print("     export ANTHROPIC_API_KEY='sk-ant-...'")
        print("     echo \"ANTHROPIC_API_KEY=sk-ant-...\" > .env")
        return EXIT_FAIL

    targets = select_targets(args)

    print(RULE)
    print("🔑 PITCHROAST CONNECTIVITY PROBE")
    print(RULE)
    print(f"  Key        {key_prefix(api_key)}")
    print(f"  Endpoint   {API_BASE}")
    print(f"  Probing    {len(targets)} model(s) @ max_tokens={PROBE_MAX_TOKENS}")

    client = anthropic.Anthropic(api_key=api_key, base_url=API_BASE)

    catalog, catalog_error = fetch_catalog(client)
    render_catalog(catalog, catalog_error, [model_id for model_id, _ in targets])

    print()
    print(THIN)
    print("📡 LIVE PROBES")
    print(THIN)

    outcomes: list[ProbeOutcome] = []
    for model_id, label in targets:
        display_name = catalog.get(model_id, label)
        outcomes.append(probe(client, model_id, display_name))
        render_outcome(outcomes[-1])

    passed = [o for o in outcomes if o.ok]
    failed = [o for o in outcomes if not o.ok]

    print()
    print(RULE)
    print(f"📋 SUMMARY — ✅ {len(passed)} reachable   ❌ {len(failed)} failed")
    print(RULE)
    for outcome in failed:
        print(f"  ❌ {outcome.model_id:<22} {outcome.failure}")
    if failed:
        print()
        print("  Fix the failures above before going on stage.")
        return EXIT_FAIL

    total_in = sum(o.input_tokens for o in passed)
    total_out = sum(o.output_tokens for o in passed)
    print(f"  Spent {total_in} input / {total_out} output tokens on this check.")
    print("  ✅ Stockholm Epicenter ready.")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🛑 Aborted.", file=sys.stderr)
        sys.exit(EXIT_INTERRUPT)
