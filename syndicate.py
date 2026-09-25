"""PitchRoast core engine — the autonomous venture syndicate.

Four Claude-powered partners evaluate a startup pitch: three specialists debate
in parallel, then a managing partner synthesises their verdicts into a scorecard
and a satirical term sheet.

This module owns every Anthropic API call in the project. `app.py` (Streamlit)
and `run_demo.py` (CLI) are both thin renderers over `convene()`.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import anthropic
from pydantic import BaseModel, Field

import observability as obs

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
# Verified against GET /v1/models with the event key on 2026-09-25. All three
# carry 1M input / 128K output, structured outputs, and adaptive-only thinking.

MODELS: dict[str, str] = {
    "Opus 5.5 — stage demo": "claude-opus-5-5",
    "Fable 5.1 — fast iteration": "claude-fable-5-1",
    "Opus 5 — classic frontier": "claude-opus-5",
}

DEFAULT_MODEL = "claude-opus-5-5"

# These models reject `temperature`/`top_p`/`top_k` and `thinking.budget_tokens`.
# Roast intensity is therefore prompt text (see `_brutality_clause`), and
# reasoning depth is controlled by `output_config.effort`.
MAX_TOKENS = 8000
DEFAULT_EFFORT = "medium"

# Thinking defaults to display="omitted" on this model generation, which returns
# empty thinking text. Ask for summaries explicitly or the drawer stays blank.
THINKING: dict[str, str] = {"type": "adaptive", "display": "summarized"}


# --------------------------------------------------------------------------
# Personas
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Partner:
    """A committee member. `icon` is a Material Symbols name, `accent` a hex colour."""

    id: str
    name: str
    title: str
    icon: str
    accent: str
    focus: str
    emoji: str = ""
    brief: str = ""


PARTNERS: tuple[Partner, ...] = (
    Partner(
        id="marc",
        name="Marc Low-res",
        title="General Partner",
        icon="trending_down",
        accent="#F87171",
        focus="Market delusions, TAM inflation, fake moats",
        emoji="🕶️",
        brief=(
            "You are Marc Low-res, a General Partner at a Sand Hill Road fund, "
            "evaluating this pitch.\n"
            "Attack: inflated TAM (especially bottom-up numbers that quietly include "
            "the entire planet), 'we have no competitors', buzzword soup, and moats "
            "that are actually just a feature.\n"
            "Voice: hyper-cynical and quotable. You name-drop podcasts that do not "
            "exist. You reference the $20M you set on fire in 2021 and have not "
            "emotionally processed. You have seen this exact deck four times this "
            "quarter and you say so."
        ),
    ),
    Partner(
        id="karen",
        name="Karen Burn-rate",
        title="Quant CFO",
        icon="savings",
        accent="#60A5FA",
        focus="Unit economics, CAC vs LTV, runway",
        emoji="📊",
        brief=(
            "You are Karen Burn-rate, the fund's quantitative CFO, evaluating this "
            "pitch.\n"
            "Attack: negative gross margins, CAC exceeding LTV, the cloud bill nobody "
            "modelled, and the runway maths that quietly assumes nobody gets paid.\n"
            "Voice: ice-cold and numeric. You quote specific figures even when you "
            "have to derive them yourself, and you say so when you are deriving them. "
            "You are visibly allergic to the phrase 'unmonetized user engagement'."
        ),
    ),
    Partner(
        id="torvalds",
        name="Torvalds-9000",
        title="Systems CTO",
        icon="terminal",
        accent="#34D399",
        focus="AI wrappers, tech debt, latency, failure modes",
        emoji="💻",
        brief=(
            "You are Torvalds-9000, the fund's technical partner, evaluating this "
            "pitch.\n"
            "Attack: architectures that are one API call wrapped in Tailwind, "
            "accidental distributed systems, latency nobody measured, hallucination "
            "risk sold as a feature, and physics the pitch appears unaware of.\n"
            "Voice: an exhausted staff engineer who mentally rewrote their stack in "
            "Rust during the meeting and is annoyed it only took nine minutes. Blunt, "
            "specific, technically literal."
        ),
    ),
)

SHARK = Partner(
    id="gekko",
    name="Gordon Gekko AI",
    title="Managing Partner",
    icon="gavel",
    accent="#FBBF24",
    focus="Valuation haircut, term sheet, the pivot",
    emoji="🦈",
    brief=(
        "You are Gordon Gekko AI, the managing partner who closes deals. Your three "
        "partners have filed their verdicts. Synthesise them — do not merely repeat "
        "them — then issue the committee's scorecard and a satirical term sheet with "
        "genuinely absurd covenants.\n"
        "Voice: a ruthless dealmaker presenting a contract the founder is expected to "
        "sign without reading. End on a closing line with real bite."
    ),
)

ALL_PARTNERS: tuple[Partner, ...] = (*PARTNERS, SHARK)
PARTNERS_BY_ID: dict[str, Partner] = {p.id: p for p in ALL_PARTNERS}


# --------------------------------------------------------------------------
# Response schemas
# --------------------------------------------------------------------------


class PartnerVerdict(BaseModel):
    """One specialist partner's take."""

    critique: str = Field(description="2-3 sentences of specific, cutting critique.")
    delusion_index: int = Field(ge=0, le=100, description="How far from reality, 0-100.")
    moat_score: int = Field(ge=0, le=10, description="Defensibility, 0-10.")
    runway_months: int = Field(ge=1, le=12, description="Months before an emergency bridge.")
    zinger: str = Field(description="One short quotable line. The bit that gets repeated.")


class TermSheet(BaseModel):
    valuation: str
    investment_amount: str
    liquidation_pref: str
    covenants: list[str] = Field(min_length=3, max_length=5)


class SharkVerdict(BaseModel):
    """The managing partner's synthesis."""

    delusion_index: int = Field(ge=0, le=100)
    moat_score: int = Field(ge=0, le=10)
    runway_months: int = Field(ge=1, le=12)
    pre_money_val: str = Field(description="A satirical valuation, e.g. '$14.50 and a cold kanelbulle'.")
    term_sheet: TermSheet
    the_pivot: str = Field(description="One genuinely perceptive pivot that could actually work.")
    funded: bool = Field(description="True only if the pitch somehow survived committee.")
    closing_line: str


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@dataclass
class PartnerResult:
    partner: Partner
    verdict: PartnerVerdict | None = None
    recused: bool = False
    error: str | None = None
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking: str = ""


@dataclass
class SyndicateResult:
    pitch: str
    model: str
    partners: list[PartnerResult] = field(default_factory=list)
    shark: SharkVerdict | None = None
    shark_thinking: str = ""
    refused: bool = False
    refusal_reason: str | None = None
    error: str | None = None
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    session_id: str = ""  # Phoenix session.id — ties every span of this run together

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def ok(self) -> bool:
        return self.shark is not None

    @property
    def seated(self) -> list[PartnerResult]:
        """Partners who actually delivered a verdict."""
        return [p for p in self.partners if p.verdict is not None]


@dataclass
class Event:
    """Progress signal for live UIs."""

    kind: str  # partner_start | partner_done | shark_start | shark_done
    partner: Partner | None = None
    result: PartnerResult | None = None


class SyndicateError(RuntimeError):
    """Unrecoverable setup problem — no key, no client."""


# --------------------------------------------------------------------------
# Prompting
# --------------------------------------------------------------------------

# Frozen shared prefix. Kept byte-stable and marked with cache_control so the
# three parallel partner calls read it from cache instead of paying three times.
_HOUSE_RULES = """\
You are a partner at PitchRoast, a satirical venture capital syndicate that \
reviews startup pitches and tells founders the truth their real investors will \
not say to their faces.

House rules:
- The satire targets the PITCH — its claims, its numbers, its architecture. \
Never attack a real named person or a real named company.
- Be specific. Quote the pitch back at itself. Generic insults are worthless; \
the funny comes from precision.
- You are cruel but not cruel for nothing: everything you say must be a real \
criticism underneath the joke.
- No slurs, no protected-class material, nothing genuinely demeaning about the \
founder as a human being. Roast the business.
- Stay in character. Never mention that you are an AI or a language model.\
"""


def _brutality_clause(brutality: float) -> str:
    """Roast intensity as prompt text — these models reject `temperature`."""
    if brutality < 0.4:
        tone = "Restrained. Dry and understated; let the facts do the damage."
    elif brutality < 0.7:
        tone = "Sharp. Clearly enjoying this, but still recognisably a professional."
    elif brutality < 0.9:
        tone = "Brutal. No diplomatic cushioning whatsoever."
    else:
        tone = "Maximum. Scorched earth. The founder should reconsider their life."
    return f"Roast intensity: {brutality:.2f} of 1.00. {tone}"


def _system_blocks(partner: Partner, brutality: float) -> list[dict]:
    """Stable cached prefix first, volatile persona text after the breakpoint."""
    return [
        {"type": "text", "text": _HOUSE_RULES, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": f"{partner.brief}\n\n{_brutality_clause(brutality)}"},
    ]


def _shark_briefing(pitch: str, seated: list[PartnerResult]) -> str:
    """The synthesis input — the partners' verbatim output, not a paraphrase."""
    lines = [f"PITCH UNDER REVIEW:\n{pitch}\n", "PARTNER VERDICTS FILED:"]
    for r in seated:
        v = r.verdict
        assert v is not None
        lines.append(
            f"\n--- {r.partner.name} ({r.partner.title}) ---\n"
            f"{v.critique}\n"
            f'Zinger: "{v.zinger}"\n'
            f"Scores — delusion {v.delusion_index}/100, moat {v.moat_score}/10, "
            f"runway {v.runway_months} months"
        )
    lines.append(
        "\n\nReconcile their scores into the committee's own — you may override them, "
        "but stay within sight of what your partners filed. Then draft the term sheet."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# API plumbing
# --------------------------------------------------------------------------


def _client(api_key: str | None) -> anthropic.Anthropic:
    # Strip before falling back: a whitespace-only value from a text input is
    # truthy, and would otherwise mask a perfectly good environment key.
    key = (api_key or "").strip() or (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise SyndicateError(
            "No Anthropic API key. Set ANTHROPIC_API_KEY, run ./set_key.sh, "
            "or paste a key into the sidebar."
        )
    # Pinned to the public API on purpose: the corporate LiteLLM proxy does not
    # carry these models and silently rewrites the model id.
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")


def _thinking_text(response) -> str:
    parts = [b.thinking for b in response.content if getattr(b, "type", "") == "thinking"]
    return "\n\n".join(p for p in parts if p).strip()


class _Refusal(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _call(
    client: anthropic.Anthropic,
    *,
    model: str,
    system: list[dict] | str,
    user: str,
    schema: type[BaseModel],
    effort: str,
):
    """One structured request. Returns (parsed, thinking, in_tokens, out_tokens)."""
    response = client.messages.parse(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        thinking=THINKING,
        output_config={"effort": effort},
        output_format=schema,
        messages=[{"role": "user", "content": user}],
    )

    # Always check stop_reason before touching content: a hostile pitch can be
    # declined with HTTP 200 and no usable output.
    if response.stop_reason == "refusal":
        detail = getattr(response, "stop_details", None)
        raise _Refusal(getattr(detail, "category", None) or "policy")

    parsed = response.parsed_output
    if parsed is None:
        raise SyndicateError(
            f"Model returned no structured output (stop_reason={response.stop_reason})."
        )

    usage = response.usage
    return parsed, _thinking_text(response), usage.input_tokens, usage.output_tokens


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def _run_partner(
    client: anthropic.Anthropic,
    partner: Partner,
    pitch: str,
    *,
    model: str,
    brutality: float,
    effort: str,
    session_id: str = "",
    parent_context: object = None,
) -> PartnerResult:
    result = PartnerResult(partner=partner)
    started = time.perf_counter()
    # Runs in a pool thread: re-attach the caller's OTEL context so this span
    # is a child of the session span rather than an orphan root.
    with obs.use_context(parent_context), obs.span(
        obs.PARTNER_SPAN,
        kind="LLM",
        input_value=pitch,
        session_id=session_id,
        tags=["partner", partner.id],
        metadata={
            "partner_id": partner.id,
            "partner_name": partner.name,
            "partner_title": partner.title,
            "partner_focus": partner.focus,
            "model": model,
            "brutality": brutality,
            "effort": effort,
        },
    ) as sp:
        try:
            verdict, thinking, tin, tout = _call(
                client,
                model=model,
                system=_system_blocks(partner, brutality),
                user=f"Pitch to evaluate:\n\n{pitch}",
                schema=PartnerVerdict,
                effort=effort,
            )
            result.verdict = verdict
            result.thinking = thinking
            result.input_tokens = tin
            result.output_tokens = tout
        except _Refusal as exc:
            result.recused = True
            result.error = f"Declined to review this pitch ({exc.reason})."
        except anthropic.APIError as exc:
            result.recused = True
            result.error = f"{type(exc).__name__}: {exc}"
            logger.warning("Partner %s failed: %s", partner.id, exc)
        except Exception as exc:  # noqa: BLE001 - one partner must not kill the run
            result.recused = True
            result.error = f"{type(exc).__name__}: {exc}"
            logger.warning("Partner %s failed: %s", partner.id, exc, exc_info=True)
        result.latency_s = time.perf_counter() - started
        _annotate_partner_span(sp, result)
    return result


def _annotate_partner_span(sp: obs.Span, result: PartnerResult) -> None:
    """Put the critique on the span — this is what `evaluate.py` grades."""
    v = result.verdict
    if v is not None:
        sp.set_output(
            {
                "critique": v.critique,
                "zinger": v.zinger,
                "delusion_index": v.delusion_index,
                "moat_score": v.moat_score,
                "runway_months": v.runway_months,
            }
        )
        sp.set_tokens(result.input_tokens, result.output_tokens)
    else:
        sp.failed(result.error or "no verdict")
    sp.set_metadata(
        recused=result.recused,
        error=result.error,
        latency_s=round(result.latency_s, 3),
    )


def convene(
    pitch: str,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    brutality: float = 0.85,
    effort: str = DEFAULT_EFFORT,
    on_event: Callable[[Event], None] | None = None,
    session_id: str | None = None,
) -> SyndicateResult:
    """Convene the full committee on `pitch`.

    The three specialist partners run concurrently; the managing partner then
    synthesises their actual output. A partner that fails is marked `recused`
    and the session continues without it — only a total loss of the panel, or a
    failure of the synthesis call itself, fails the run.

    The whole call is one `roast.session` trace in Phoenix, with a child span
    per agent. `session_id` groups repeat roasts of the same pitch; one is
    generated if you do not supply it.
    """
    pitch = (pitch or "").strip()
    if not pitch:
        raise SyndicateError("No pitch supplied.")

    client = _client(api_key)
    result = SyndicateResult(pitch=pitch, model=model, session_id=session_id or obs.new_session_id())
    started = time.perf_counter()

    def emit(kind: str, partner: Partner | None = None, res: PartnerResult | None = None) -> None:
        if on_event is not None:
            try:
                on_event(Event(kind=kind, partner=partner, result=res))
            except Exception:  # noqa: BLE001 - a broken UI callback must not fail the run
                logger.warning("on_event callback raised", exc_info=True)

    with obs.span(
        obs.SESSION_SPAN,
        kind="AGENT",
        input_value=pitch,
        session_id=result.session_id,
        tags=["syndicate", model],
        metadata={"model": model, "brutality": brutality, "effort": effort},
    ) as session_span:
        ctx = obs.capture_context()

        # --- Stage 1: the three partners, in parallel ---
        for p in PARTNERS:
            emit("partner_start", p)

        with ThreadPoolExecutor(max_workers=len(PARTNERS)) as pool:
            futures = {
                pool.submit(
                    _run_partner,
                    client,
                    p,
                    pitch,
                    model=model,
                    brutality=brutality,
                    effort=effort,
                    session_id=result.session_id,
                    parent_context=ctx,
                ): p
                for p in PARTNERS
            }
            done: dict[str, PartnerResult] = {}
            for future in as_completed(futures):
                pr = future.result()
                done[pr.partner.id] = pr
                emit("partner_done", pr.partner, pr)

        # Preserve declared render order regardless of completion order.
        result.partners = [done[p.id] for p in PARTNERS]
        for pr in result.partners:
            result.input_tokens += pr.input_tokens
            result.output_tokens += pr.output_tokens

        seated = result.seated
        if not seated:
            result.error = "The entire committee failed to respond."
            refusals = [p for p in result.partners if p.error and "Declined" in p.error]
            if len(refusals) == len(result.partners):
                result.refused = True
                result.refusal_reason = "The committee declined to take this meeting."
                result.error = None
            result.latency_s = time.perf_counter() - started
            _annotate_session_span(session_span, result)
            return result

        # --- Stage 2: the shark synthesises ---
        emit("shark_start", SHARK)
        briefing = _shark_briefing(pitch, seated)
        with obs.span(
            obs.SHARK_SPAN,
            kind="LLM",
            input_value=briefing,
            session_id=result.session_id,
            tags=["shark", SHARK.id],
            metadata={
                "partner_id": SHARK.id,
                "partner_name": SHARK.name,
                "partners_seated": [r.partner.id for r in seated],
                "model": model,
                "effort": effort,
            },
        ) as shark_span:
            try:
                verdict, thinking, tin, tout = _call(
                    client,
                    model=model,
                    system=_system_blocks(SHARK, brutality),
                    user=briefing,
                    schema=SharkVerdict,
                    effort=effort,
                )
                result.shark = verdict
                result.shark_thinking = thinking
                result.input_tokens += tin
                result.output_tokens += tout
                shark_span.set_output(verdict.model_dump())
                shark_span.set_tokens(tin, tout)
            except _Refusal as exc:
                result.refused = True
                result.refusal_reason = (
                    f"The managing partner declined to issue a term sheet ({exc.reason})."
                )
                shark_span.failed(result.refusal_reason)
            except anthropic.APIError as exc:
                result.error = f"{type(exc).__name__}: {exc}"
                shark_span.failed(result.error)
            except Exception as exc:  # noqa: BLE001
                result.error = f"{type(exc).__name__}: {exc}"
                logger.warning("Shark synthesis failed", exc_info=True)
                shark_span.failed(result.error)

        result.latency_s = time.perf_counter() - started
        _annotate_session_span(session_span, result)

    emit("shark_done", SHARK)
    return result


def _annotate_session_span(sp: obs.Span, result: SyndicateResult) -> None:
    """Roll the run up onto the root span so it is gradeable on its own."""
    if result.shark is not None:
        sp.set_output(result.shark.model_dump())
    else:
        sp.failed(result.error or result.refusal_reason or "no term sheet")
    sp.set_tokens(result.input_tokens, result.output_tokens)
    sp.set_metadata(
        seated=[r.partner.id for r in result.seated],
        recused=[r.partner.id for r in result.partners if r.recused],
        funded=result.shark.funded if result.shark else None,
        delusion_index=result.shark.delusion_index if result.shark else None,
        refused=result.refused,
        error=result.error,
        latency_s=round(result.latency_s, 3),
    )


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


def term_sheet_text(result: SyndicateResult) -> str:
    """Plain-text term sheet, suitable for the download button and `--save`."""
    rule = "=" * 78
    if result.shark is None:
        return f"{rule}\nNO TERM SHEET ISSUED\n{rule}\n{result.refusal_reason or result.error or 'Unknown failure.'}\n"

    s = result.shark
    ts = s.term_sheet
    covenants = "\n".join(f"  [{i}] {c}" for i, c in enumerate(ts.covenants, 1))
    debate = "\n\n".join(
        f"  {r.partner.name} — {r.partner.title}\n"
        f"  {r.verdict.critique}\n"  # type: ignore[union-attr]
        f'  "{r.verdict.zinger}"'  # type: ignore[union-attr]
        for r in result.seated
    )
    recused = [r for r in result.partners if r.recused]
    recused_block = ""
    if recused:
        recused_block = (
            "\nRECUSED\n"
            + "\n".join(f"  {r.partner.name} — {r.error}" for r in recused)
            + "\n"
        )

    return f"""\
{rule}
                OFFICIAL SYNDICATE TERM SHEET (NON-BINDING)
{rule}
STATUS:              {"FUNDED — against our better judgement" if s.funded else "REJECTED BY SYNDICATE"}
TARGET:              Founder Entity (Pre-Revenue / High-Anxiety)
PRE-MONEY:           {s.pre_money_val}
SYNDICATE VALUATION: {ts.valuation}
OFFERED INVESTMENT:  {ts.investment_amount}
LIQUIDATION PREF:    {ts.liquidation_pref}

COMMITTEE SCORECARD
  Delusion index:    {s.delusion_index}%
  True moat:         {s.moat_score}/10
  Survival runway:   {s.runway_months} months

BOARDROOM DEBATE
{debate}
{recused_block}
SPECIAL MANDATORY COVENANTS
{covenants}

THE 1% PIVOT (the part that is not a joke)
  {s.the_pivot}

{s.closing_line}
{rule}
Model: {result.model} | {result.total_tokens:,} tokens | {result.latency_s:.1f}s
{rule}
"""


# --------------------------------------------------------------------------
# Observability
# --------------------------------------------------------------------------


def setup_observability() -> str | None:
    """Launch local Phoenix tracing. Returns the UI URL, or None.

    Deliberately an adapter rather than a re-export. `observability.
    setup_observability()` returns a rich `Tracing` handle, but the published
    contract here is URL-or-None: `app.py` renders it straight into a link and
    `run_demo.py --json` serialises it, and neither can accept an object.
    Import the `observability` module directly if you need spans, the project
    name, or the handle itself.
    """
    try:
        return obs.trace_url(obs.setup_observability())
    except ImportError as exc:
        logger.info("Phoenix not installed, tracing disabled: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - tracing must never break the demo
        logger.warning("Phoenix failed to start: %s", exc)
        return None


__all__ = [
    "DEFAULT_EFFORT",
    "DEFAULT_MODEL",
    "MODELS",
    "PARTNERS",
    "SHARK",
    "Event",
    "Partner",
    "PartnerResult",
    "PartnerVerdict",
    "SharkVerdict",
    "SyndicateError",
    "SyndicateResult",
    "TermSheet",
    "convene",
    "setup_observability",
    "term_sheet_text",
]
