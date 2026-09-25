"""Token → credit arithmetic for the Syndicate Observatory.

Deliberately free of Streamlit and of `syndicate`: this is plain numbers, so it
is unit-testable (`test_modes.py`) and safe to import from anywhere.

Two things in here are judgement calls rather than facts, and both are surfaced
in the UI rather than hidden:

1. **Prices.** `claude-opus-5-5` — the stage-demo model — has no per-token rate
   in any table available offline (BUILD_SPEC.md §3 says to confirm it in the
   Console). Rather than quietly inventing one, an unlisted model is priced at
   the Opus tier and marked `confirmed=False`, which the Observatory renders as
   "assumed". Set `PITCHROAST_PRICING` to replace a guess with the real number.
2. **The euro rate.** Credits are billed in USD; the hackathon voucher is €100.
   One fixed conversion, overridable, shown as an assumption in the UI.

What this measures is also narrower than "credits left on the voucher": it is
what *this Streamlit process* has spent since it started. CLI demos, eval runs
and anything billed before the app booted are invisible to it.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from syndicate import SyndicateResult

logger = logging.getLogger(__name__)

MILLION = 1_000_000


@dataclass(frozen=True)
class Price:
    """List price in USD per million tokens.

    `confirmed` is False when this is our assumption rather than a published
    rate. The Observatory labels those, so nobody quotes a guess on stage.
    """

    input_usd: float
    output_usd: float
    confirmed: bool = True


# Published Anthropic list prices, USD per million tokens.
PUBLISHED: dict[str, Price] = {
    "claude-fable-5-1": Price(10.00, 50.00),
    "claude-opus-5": Price(5.00, 25.00),
    "claude-sonnet-5": Price(2.00, 10.00),
    "claude-haiku-4-5": Price(1.00, 5.00),
}

# Anything not in the table above (notably claude-opus-5-5) is charged at the
# Opus tier and flagged as an assumption.
ASSUMED = Price(5.00, 25.00, confirmed=False)

DEFAULT_VOUCHER_EUR = 100.0
DEFAULT_EUR_PER_USD = 0.92


def _env_float(name: str, fallback: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return fallback
    try:
        value = float(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using %s", name, raw, fallback)
        return fallback
    if value <= 0:
        logger.warning("%s=%r must be positive; using %s", name, raw, fallback)
        return fallback
    return value


def overrides() -> dict[str, Price]:
    """Operator-supplied prices from `PITCHROAST_PRICING`.

    JSON, model id → `[input_per_mtok, output_per_mtok]`:

        PITCHROAST_PRICING='{"claude-opus-5-5": [5, 25]}'

    An override counts as confirmed — someone read it off the Console.
    """
    raw = (os.getenv("PITCHROAST_PRICING") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return {
            str(model): Price(float(pair[0]), float(pair[1]))
            for model, pair in parsed.items()
        }
    except Exception as exc:  # noqa: BLE001 - a bad override must not break the app
        logger.warning("Ignoring unparseable PITCHROAST_PRICING (%s)", exc)
        return {}


def price_for(model: str) -> Price:
    """Per-token price for `model`: override, then published, then assumed."""
    return overrides().get(model) or PUBLISHED.get(model) or ASSUMED


def eur_per_usd() -> float:
    return _env_float("PITCHROAST_EUR_PER_USD", DEFAULT_EUR_PER_USD)


def voucher_eur() -> float:
    return _env_float("PITCHROAST_VOUCHER_EUR", DEFAULT_VOUCHER_EUR)


def to_eur(usd: float) -> float:
    return usd * eur_per_usd()


def usd_of(model: str, input_tokens: int, output_tokens: int) -> float:
    """Undiscounted list cost of one set of token counts.

    No cache-read discount is applied. `syndicate._HOUSE_RULES` sits under the
    minimum cacheable prefix, so no request in this app has ever produced a
    cache hit — pricing the cached path would overstate the saving.
    """
    price = price_for(model)
    return (
        input_tokens * price.input_usd + output_tokens * price.output_usd
    ) / MILLION


@dataclass(frozen=True)
class RunCost:
    """One convened committee, costed. Appended to the session's spend log."""

    model: str
    input_tokens: int
    output_tokens: int
    usd: float
    latency_s: float
    seats: int
    session_id: str
    confirmed: bool

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def eur(self) -> float:
        return to_eur(self.usd)


def cost_of(result: SyndicateResult) -> RunCost:
    """Cost a finished `SyndicateResult`.

    Counts every seat that burned tokens, including partners who errored after
    the call went out — a failed roast is not a free one.
    """
    return RunCost(
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        usd=usd_of(result.model, result.input_tokens, result.output_tokens),
        latency_s=result.latency_s,
        seats=len(result.partners),
        session_id=result.session_id,
        confirmed=price_for(result.model).confirmed,
    )


@dataclass(frozen=True)
class Totals:
    """The spend log rolled up for the telemetry panel."""

    runs: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    assumed_prices: bool = False

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def eur(self) -> float:
        return to_eur(self.usd)

    @property
    def voucher_used(self) -> float:
        """Fraction of the voucher spent, clamped to 0.0-1.0 for `st.progress`."""
        voucher = voucher_eur()
        if voucher <= 0:
            return 0.0
        return min(max(self.eur / voucher, 0.0), 1.0)

    @property
    def voucher_left_eur(self) -> float:
        return max(voucher_eur() - self.eur, 0.0)


def totals(runs: list[RunCost]) -> Totals:
    if not runs:
        return Totals()
    return Totals(
        runs=len(runs),
        input_tokens=sum(r.input_tokens for r in runs),
        output_tokens=sum(r.output_tokens for r in runs),
        usd=sum(r.usd for r in runs),
        assumed_prices=any(not r.confirmed for r in runs),
    )


def eur(amount_usd: float) -> str:
    """€-formatted, with enough decimals that a single roast is not '€0.00'."""
    value = to_eur(amount_usd)
    return f"€{value:.4f}" if 0 < value < 0.01 else f"€{value:.2f}"
