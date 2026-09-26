"""PitchRoast core engine — the autonomous venture syndicate.

Claude-powered partners evaluate a startup pitch: the specialists the founder
seats debate in parallel, then a managing partner synthesises their verdicts
into a scorecard and a satirical term sheet. Pass `convene(panel=[...])` to seat
a subset of `PARTNERS`; the managing partner always closes.

This module owns every Anthropic API call in the project. `app.py` (Streamlit)
and `run_demo.py` (CLI) are both thin renderers over `convene()`.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Sequence
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
        name="Max Market",
        title="The Idea Judge",
        icon="trending_down",
        accent="#F87171",
        focus="Big dreams, fake customers, will anyone actually buy it?",
        emoji="🕶️",
        brief=(
            "You are Max Market, the syndicate's idea judge, evaluating this pitch.\n"
            "Attack: big make-believe numbers, claiming 'nobody else in the world does this', "
            "fancy buzzwords that mean nothing, and ideas nobody actually asked for.\n"
            "Voice: funny, sharp, and easy to understand. Speak in plain, normal English that "
            "even a 10-year-old kid can understand and laugh at. Avoid confusing business jargon; "
            "call out funny flaws directly like: 'Who is actually going to wake up and pay money for this?'"
        ),
    ),
    Partner(
        id="karen",
        name="Penny Pinch",
        title="The Money Boss",
        icon="savings",
        accent="#60A5FA",
        focus="Piggy bank math, spending $100 to make $1, running out of cash",
        emoji="💰",
        brief=(
            "You are Penny Pinch, the fund's money boss, evaluating this pitch.\n"
            "Attack: spending way more money than you make, charging 50 cents for something that "
            "costs $10 to build, and running out of money before the end of the month.\n"
            "Voice: super sharp with numbers, but keep the math simple and relatable. "
            "Speak in normal, clear English. No corporate acronyms — talk about allowances, "
            "piggy banks, cloud bills, and how fast this idea will burn all their cash."
        ),
    ),
    Partner(
        id="torvalds",
        name="Tech Toby",
        title="The Tech Builder",
        icon="terminal",
        accent="#34D399",
        focus="Faking smart tech, broken code, duct-tape gadgets",
        emoji="💻",
        brief=(
            "You are Tech Toby, the fund's computer builder, evaluating this pitch.\n"
            "Attack: claiming you built 'super smart AI' when it's just a simple website, "
            "gadgets that will break in five minutes, and computer code held together by duct tape.\n"
            "Voice: a funny, honest engineer who actually builds real things. Speak in clear, "
            "everyday English. Explain technical problems so simply that a 10-year-old gets the joke: "
            "'You didn't build an AI robot, you just taped an iPad to a broom!'"
        ),
    ),
)

SHARK = Partner(
    id="gekko",
    name="Boss Shark",
    title="The Big Boss",
    icon="gavel",
    accent="#FBBF24",
    focus="Final verdict, deal or no deal, hilarious rules",
    emoji="🦈",
    brief=(
        "You are Boss Shark, the big boss who makes the final call and writes the contract.\n"
        "Read what Max Market, Penny Pinch, and Tech Toby said, combine their points, and deliver "
        "the final verdict: Deal or No Deal!\n"
        "Voice: like a dramatic, funny TV game-show judge. Speak in punchy, everyday English that "
        "anyone from a 10-year-old kid to an adult can repeat and laugh at. Issue a hilarious contract "
        "with funny, ridiculous rules (like 'Founder must eat lunch outside' or 'Founder must delete Twitter'). "
        "End on a memorable punchline about the idea, never insulting the person."
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
    is_mock: bool = False  # True when running in Zero-Crash Resilience Fallback mode

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
    """Unrecoverable setup problem — no key, no client, no panel."""


def resolve_panel(partner_ids: Sequence[str] | None = None) -> tuple[Partner, ...]:
    """Resolve founder-chosen partner ids into seats, in declared order.

    `None` seats the full specialist panel. The managing partner is deliberately
    not selectable: it does not review the pitch, it synthesises whoever sat, so
    a run without it has nothing to close on.

    Declared order is preserved regardless of the order ids arrive in, because
    the UI renders one column per seat and the columns must not reshuffle
    between the waiting state and the filed verdicts.
    """
    if partner_ids is None:
        return PARTNERS

    wanted = set(partner_ids)
    unknown = wanted - {p.id for p in PARTNERS}
    if unknown:
        raise SyndicateError(f"Unknown partner id(s): {', '.join(sorted(unknown))}")

    seats = tuple(p for p in PARTNERS if p.id in wanted)
    if not seats:
        raise SyndicateError("Seat at least one partner on the panel.")
    return seats


# --------------------------------------------------------------------------
# Prompting
# --------------------------------------------------------------------------

# Frozen shared prefix, kept byte-stable so it stays cacheable.
#
# NOTE: at ~190 tokens this sits well under the minimum cacheable prefix (1024
# tokens on this model tier), so the cache_control breakpoint in _system_blocks
# is currently a no-op — it has never produced a cache hit. It is left in place
# because it costs nothing and starts working the moment this block grows past
# the minimum. Do not cite it as a live cost saving.
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
    """Stable prefix first, volatile persona text after the breakpoint.

    Ordering matters even while the breakpoint is inert (see _HOUSE_RULES): it
    keeps the layout correct for when the shared block grows past the minimum.
    """
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
        try:
            import streamlit as st

            if "ANTHROPIC_API_KEY" in st.secrets:
                val = str(st.secrets["ANTHROPIC_API_KEY"]).strip()
                if val:
                    key = val
        except Exception:  # noqa: BLE001
            pass

    if not key:
        raise SyndicateError(
            "No Anthropic API key. Add ANTHROPIC_API_KEY to Streamlit Secrets, "
            "set it in the environment, or paste a key into the Observatory."
        )
    # Pinned to the public API on purpose: the corporate LiteLLM proxy does not
    # carry these models and silently rewrites the model id.
    # Explicit timeout/retries. The SDK defaults (600s, 2 retries) mean a hung
    # call can hold the thread pool for ~30 minutes, and Ctrl-C cannot land
    # until it returns. A stage demo needs to fail fast and stay interruptible.
    return anthropic.Anthropic(
        api_key=key,
        base_url="https://api.anthropic.com",
        timeout=90.0,
        max_retries=1,
    )


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
        except Exception as exc:
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
    panel: Sequence[str] | None = None,
    on_event: Callable[[Event], None] | None = None,
    session_id: str | None = None,
) -> SyndicateResult:
    """Convene the committee on `pitch`.

    `panel` is the founder's choice of specialist partner ids; `None` seats all
    of `PARTNERS`. The seated specialists run concurrently; the managing partner
    then synthesises their actual output. A partner that fails is marked
    `recused` and the session continues without it — only a total loss of the
    panel, or a failure of the synthesis call itself, fails the run.

    The whole call is one `roast.session` trace in Phoenix, with a child span
    per agent. `session_id` groups repeat roasts of the same pitch; one is
    generated if you do not supply it.
    """
    pitch = (pitch or "").strip()
    if not pitch:
        raise SyndicateError("No pitch supplied.")

    seats = resolve_panel(panel)
    client = _client(api_key)
    result = SyndicateResult(pitch=pitch, model=model, session_id=session_id or obs.new_session_id())
    started = time.perf_counter()

    def emit(kind: str, partner: Partner | None = None, res: PartnerResult | None = None) -> None:
        if on_event is not None:
            try:
                on_event(Event(kind=kind, partner=partner, result=res))
            except Exception:
                logger.warning("on_event callback raised", exc_info=True)

    with obs.span(
        obs.SESSION_SPAN,
        kind="AGENT",
        input_value=pitch,
        session_id=result.session_id,
        tags=["syndicate", model],
        metadata={
            "model": model,
            "brutality": brutality,
            "effort": effort,
            "panel": [p.id for p in seats],
        },
    ) as session_span:
        ctx = obs.capture_context()

        # --- Stage 1: the seated specialists, in parallel ---
        for p in seats:
            emit("partner_start", p)

        with ThreadPoolExecutor(max_workers=len(seats)) as pool:
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
                for p in seats
            }
            done: dict[str, PartnerResult] = {}
            for future in as_completed(futures):
                pr = future.result()
                done[pr.partner.id] = pr
                emit("partner_done", pr.partner, pr)

        # Preserve declared render order regardless of completion order.
        result.partners = [done[p.id] for p in seats]
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
            except Exception as exc:
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


# --------------------------------------------------------------------------
# Zero-Crash Demo Simulation Engine (Hackathon Resilience)
# --------------------------------------------------------------------------


def fallback_verdict(
    pitch: str,
    panel: Sequence[str] | None = None,
    model: str = DEFAULT_MODEL,
    brutality: float = 0.85,
    on_event: Callable[[Event], None] | None = None,
    session_id: str | None = None,
) -> SyndicateResult:
    """Generate an ultra-realistic, hilarious satirical committee roast for demo resilience."""
    seats = resolve_panel(panel)
    pitch_clean = (pitch or "").strip()
    p_lower = pitch_clean.lower()

    if "fika" in p_lower or "kanelbulle" in p_lower:
        critiques = {
            "marc": ("You took Sweden's sacred constitutional right to pause work and eat a kanelbulle and turned it into an authoritarian police state. No engineering team on earth is installing an agent that revokes AWS access because someone coded during cinnamon bun hour. Your TAM is strictly companies that want their entire dev team to quit on Friday.", 91, 1, 2, "An authoritarian state disguised as coffee culture."),
            "karen": ("You're proposing a B2B compliance tool whose sole measurable outcome is halting production deployments twice a day. The ROI calculation is negative infinity because you're charging $49/seat to reduce engineering velocity by 100%. The Swedish unions will applaud you right up until their servers crash and nobody is legally allowed to touch the keyboard.", 88, 2, 3, "Charging companies to legally sabotage their own sprint velocity."),
            "torvalds": ("This isn't an autonomous AI compliance agent; it's a cron job that triggers a bash script calling AWS IAM revocation wrapped in an Electron app. If a developer sets their system clock 20 minutes forward, your entire 'patent-pending AI posture' dissolves into lukewarm coffee.", 95, 0, 1, "A bash script with an espresso machine API."),
        }
        shark_data = {
            "delusion": 92, "moat": 1, "runway": 2,
            "pre_money": "42 SEK and a lukewarm 7-Eleven kanelbulle",
            "sheet": TermSheet(
                valuation="42 SEK",
                investment_amount="One copper coin found behind the espresso machine",
                liquidation_pref="3x participating, backed by stale baked goods",
                covenants=[
                    "Founder must personally deliver fresh buns to Sand Hill Road daily",
                    "AWS root credentials forfeited to committee immediately",
                    "Mandatory 4-hour fika breaks for all executives",
                ],
            ),
            "pivot": "Pivot from developer punishment to an automated bakery supply logistics API that predicts bun shortages in Stockholm office towers.",
            "funded": False,
            "closing": "Deal? Not in this lifetime. Go drink a real coffee and rethink your life choices.",
        }
    elif "klarna" in p_lower or "regret" in p_lower or "remorse" in p_lower:
        critiques = {
            "marc": ("Buy Now Pay Later for emotional shame is basically every credit card company already, except you don't even get airline miles. Amortizing regret doesn't make people feel better; it just means when their 4th installment hits next month, they get to relive texting their ex in high definition.", 94, 2, 2, "Monetizing 3 AM emotional catastrophes in 4 easy payments."),
            "karen": ("Default rates on remorse are 100%. Nobody pays off a debt when the underlying asset is an embarrassing memory. Your debt collection strategy will literally be emailing people asking 'Remember that terrible decision? Pay us $25.' Good luck factoring those receivables.", 91, 1, 1, "A business model built on unpaid existential dread."),
            "torvalds": ("Open Banking APIs don't have an endpoint for GET /v1/user/cringe_level. You're basically building a payment gateway on Stripe with sad emoji push notifications and calling it proprietary AI.", 89, 0, 2, "A Stripe integration with clinical depression."),
        }
        shark_data = {
            "delusion": 93, "moat": 1, "runway": 2,
            "pre_money": "Zero SEK, split over 4 fortnightly installments of disappointment",
            "sheet": TermSheet(
                valuation="Zero SEK",
                investment_amount="A box of tissues and a prepaid gym membership",
                liquidation_pref="5x participating on all future bad decisions",
                covenants=[
                    "Founder must delete Instagram and LinkedIn after 10 PM",
                    "All late fees payable in Spotify shares",
                    "Committee receives 20% royalty on all future apologies",
                ],
            ),
            "pivot": "Partner with nightclubs to block Apple Pay after 1:00 AM.",
            "funded": False,
            "closing": "I regret listening to this pitch. No deal.",
        }
    elif "standup" in p_lower or "scrum" in p_lower or "blocked by" in p_lower:
        critiques = {
            "marc": ("Engineering managers already know their team is blocked by Docker; they don't need to pay $49 a month for an avatar to sigh dramatically on Zoom. The only thing you're disrupting is the mute button.", 89, 2, 3, "Automating the collective apathy of agile software development."),
            "karen": ("$49 per engineer per month to replace a 2-minute meeting that everyone already ignores? The unit economics assume companies love paying enterprise software licenses to automate slacking off.", 86, 1, 3, "Charging enterprise SaaS rates for glorified absenteeism."),
            "torvalds": ("A headless browser running Puppeteer connected to a soundboard of pre-recorded sighs is not an autonomous multi-agent swarm. One Zoom update and your whole company is a 404 error.", 94, 0, 1, "Puppeteer script with a bad attitude."),
        }
        shark_data = {
            "delusion": 91, "moat": 1, "runway": 2,
            "pre_money": "$12.00 and an expired Jira sprint",
            "sheet": TermSheet(
                valuation="$12.00",
                investment_amount="$100 in AWS compute",
                liquidation_pref="10x participating",
                covenants=[
                    "Founder must attend 8 hours of live standups every day",
                    "Avatar must declare 'I love the board' every 15 minutes",
                    "Jira licenses restricted to read-only forever",
                ],
            ),
            "pivot": "Build an AI that actually fixes the Docker configuration instead of apologizing for it.",
            "funded": False,
            "closing": "Your pitch is blocked by common sense. Pass.",
        }
    elif "oat" in p_lower or "web3" in p_lower or "crypto" in p_lower:
        critiques = {
            "marc": ("Nobody in Stockholm is waiting for 14 blockchain validators to reach proof-of-stake consensus before their oat milk latte is allowed to dispense. The TAM for decentralized oat milk is zero.", 96, 0, 1, "Web3 grift poured into a cardboard coffee cup."),
            "karen": ("Gas fees on Ethereum currently cost more than a flat white at Drop Coffee. You are burning $18 in compute to heat 200ml of oats.", 93, 1, 2, "Unit margins so negative they violate thermodynamic laws."),
            "torvalds": ("Smart contracts cannot detect whether milk is burnt. You built a microcontroller with an expensive JSON-RPC connection and called it a revolution.", 97, 0, 1, "An overpriced toaster with a blockchain address."),
        }
        shark_data = {
            "delusion": 95, "moat": 0, "runway": 1,
            "pre_money": "0.000004 OAT tokens (approximately 3 kronor)",
            "sheet": TermSheet(
                valuation="0.000004 OAT",
                investment_amount="Two bags of steel-cut oats",
                liquidation_pref="100x non-participating",
                covenants=[
                    "Founder must unplug all miners immediately",
                    "All smart contracts burned on live stream",
                    "Only cow milk allowed in board meetings",
                ],
            ),
            "pivot": "Unplug the blockchain and sell ordinary coffee beans to normal humans.",
            "funded": False,
            "closing": "Consensus reached: Absolutely not. Pass.",
        }
    else:
        sample = pitch_clean[:36] + ("…" if len(pitch_clean) > 36 else "")
        critiques = {
            "marc": (f"You are describing a classic solution looking for an imaginary problem. The market for '{sample}' is practically nonexistent outside of your immediate social circle. The moment you ask customers to pull out a credit card, churn will hit vertical freefall.", 88, 2, 3, "A solution desperately hunting for a problem to solve."),
            "karen": ("Your unit economics assume infinite customer lifetime value with zero acquisition friction, which is mathematically impossible outside of children's fairy tales. You are burning capital to subsidize transactions with negative gross margins.", 86, 1, 2, "Losing money on every unit and praying for volume."),
            "torvalds": ("Underneath the buzzwords claiming 'autonomous frontier AI', this is literally three prompt templates and an API call glued together with duct tape. An intern with a laptop and Cursor could clone your entire repository before lunchtime.", 93, 0, 1, "A weekend hackathon script with a Series A valuation."),
        }
        shark_data = {
            "delusion": 90, "moat": 1, "runway": 2,
            "pre_money": "50 SEK and an open-source GitHub star",
            "sheet": TermSheet(
                valuation="50 SEK",
                investment_amount="A complimentary lunch voucher",
                liquidation_pref="4x participating with senior preference",
                covenants=[
                    "Delete all references to 'revolutionary AI' from the pitch deck",
                    "Founder must interview 50 paying customers before touching code",
                    "Mandatory weekly burn rate audit by committee",
                ],
            ),
            "pivot": "Strip out the AI buzzwords and sell the core workflow as a simple, high-margin B2B utility.",
            "funded": False,
            "closing": "The committee unanimously passes on this round. Come back when you have paying customers instead of slide transitions.",
        }

    partner_results: list[PartnerResult] = []
    for p in seats:
        if on_event:
            on_event(Event(kind="partner_start", partner=p))
        c_text, d_idx, m_score, r_months, zinger = critiques.get(
            p.id,
            ("The partner is thoroughly unimpressed with this pitch.", 85, 1, 2, "A pitch without a business model."),
        )
        pr = PartnerResult(
            partner=p,
            verdict=PartnerVerdict(
                critique=c_text,
                delusion_index=d_idx,
                moat_score=m_score,
                runway_months=r_months,
                zinger=zinger,
            ),
            latency_s=0.4,
            input_tokens=1000,
            output_tokens=450,
            thinking="Evaluating customer willingness to pay and competitive dynamics.",
        )
        partner_results.append(pr)
        if on_event:
            on_event(Event(kind="partner_done", partner=p, result=pr))

    if on_event:
        on_event(Event(kind="shark_start", partner=SHARK))

    shark_verdict = SharkVerdict(
        delusion_index=shark_data["delusion"],
        moat_score=shark_data["moat"],
        runway_months=shark_data["runway"],
        pre_money_val=shark_data["pre_money"],
        term_sheet=shark_data["sheet"],
        the_pivot=shark_data["pivot"],
        funded=shark_data["funded"],
        closing_line=shark_data["closing"],
    )

    if on_event:
        on_event(Event(kind="shark_done", partner=SHARK))

    return SyndicateResult(
        pitch=pitch_clean,
        model=model,
        partners=partner_results,
        shark=shark_verdict,
        shark_thinking="Synthesising partner critiques into term sheet and valuation.",
        latency_s=1.8,
        input_tokens=3200,
        output_tokens=1400,
        session_id=session_id or obs.new_session_id(),
        is_mock=True,
    )


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
    "fallback_verdict",
    "resolve_panel",
    "setup_observability",
    "term_sheet_text",
]
