"""🔬 Syndicate Observatory — the entry point for judges and the engine room.

Everything the Hot Seat deliberately hides lives here: the Phoenix trace hub,
token and credit telemetry, model and effort orchestration, the panel
concurrency dial, Claude's own deliberation traces, and the LLM-judge evaluator.

The verdict at the bottom is the *same* verdict the founder saw — it is read
from session state, not re-generated — rendered with `technical=True` so every
card carries its latency, token count and reasoning drawer. Flipping modes
never costs an API call.
"""

from __future__ import annotations

import logging
import os
import socket
from urllib.parse import urlsplit

import streamlit as st

import board
import costs
import observability as obs
import state
from syndicate import PARTNERS_BY_ID, SHARK

logger = logging.getLogger(__name__)

DEFAULT_PHOENIX_PORT = 6006


# --------------------------------------------------------------------------
# Phoenix daemon probes
# --------------------------------------------------------------------------


def _endpoint(handle: obs.Tracing) -> str:
    """Where Phoenix is, or where it would be if it came up."""
    if handle.url:
        return handle.url
    port = (os.getenv("PHOENIX_PORT") or "").strip() or str(DEFAULT_PHOENIX_PORT)
    return f"http://localhost:{port}"


@st.cache_data(ttl=5, show_spinner=False)
def _probe(base: str) -> tuple[bool, bool]:
    """`(port accepting connections, /healthz answered 200)`.

    Cached for five seconds: this runs on every rerun, including the ones a
    keystroke in the pitch box triggers, and two syscalls per keypress is two
    too many. Short TTL so "I just restarted Phoenix" still shows up promptly.
    """
    parts = urlsplit(base)
    host = parts.hostname or "localhost"
    port = parts.port or DEFAULT_PHOENIX_PORT

    open_port = False
    try:
        with socket.create_connection((host, port), timeout=0.4):
            open_port = True
    except OSError:
        return False, False

    try:
        import urllib.request

        with urllib.request.urlopen(f"{base.rstrip('/')}/healthz", timeout=1.5) as resp:
            return open_port, resp.status == 200
    except Exception:  # noqa: BLE001 - something is on the port, but not Phoenix
        return open_port, False


def _trace_tree(result) -> str:
    """The span tree `convene()` just wrote, drawn from the result it returned.

    Rendered from local data on purpose: reading it back out of Phoenix would
    add a network call to every rerun, and the shape is fixed by
    `observability.py` anyway. What Phoenix holds is this plus the raw
    Anthropic instrumentor spans underneath each leaf.
    """
    lines = [
        f"{obs.SESSION_SPAN}  [AGENT]  session={result.session_id or '—'}",
        f"│   {result.latency_s:.1f}s · {result.total_tokens:,} tokens · {result.model}",
    ]
    for item in result.partners:
        mark = "voted" if item.verdict is not None else "ERROR"
        lines.append(
            f"├── {obs.PARTNER_SPAN}  [LLM]  {item.partner.id:<9} {mark:<6} "
            f"{item.latency_s:>5.1f}s  "
            f"{item.input_tokens:>6,} in / {item.output_tokens:>6,} out"
        )
    shark_mark = "closed" if result.shark is not None else "ERROR"
    lines.append(f"└── {obs.SHARK_SPAN}  [LLM]  {SHARK.id:<9} {shark_mark}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Panels
# --------------------------------------------------------------------------


def _status_strip(handle: obs.Tracing, reason: str) -> None:
    cols = st.columns(4)
    cols[0].metric(
        "Tracing",
        "Live" if handle.enabled else "Off",
        border=True,
        help=reason or f"Phoenix project {handle.project!r}",
    )
    cols[1].metric("Model", state.model_id(), border=True, help="Next roast.")
    cols[2].metric(
        "Effort",
        state.effort(),
        border=True,
        help="output_config.effort — reasoning depth.",
    )
    cols[3].metric(
        "Seats",
        f"{len(state.panel())} + 1",
        border=True,
        help="Parallel partner calls, plus the managing partner's synthesis.",
    )


def _phoenix_hub(handle: obs.Tracing, reason: str) -> None:
    base = _endpoint(handle)
    port_open, healthy = _probe(base)

    with st.container(border=True):
        st.subheader("Arize Phoenix OSS hub", icon=":material/timeline:")

        st.link_button(
            "Open Phoenix",
            f"{base.rstrip('/')}/projects",
            icon=":material/open_in_new:",
            type="primary",
            width="stretch",
            disabled=not port_open,
        )

        with st.container(horizontal=True, wrap=True):
            if handle.enabled:
                st.badge("Instrumented", icon=":material/check_circle:", color="green")
            else:
                st.badge("Not instrumented", icon=":material/error:", color="red")
            if healthy:
                st.badge("Daemon healthy", icon=":material/favorite:", color="green")
            elif port_open:
                st.badge("Port open, no /healthz", icon=":material/warning:", color="orange")
            else:
                st.badge("Port closed", icon=":material/cancel:", color="gray")
            st.badge(
                "In-process" if handle.launched else "Adopted",
                icon=":material/memory:",
                color="blue",
            )

        st.caption(f"{base} · project `{handle.project}`")
        if not handle.enabled:
            st.caption(f":red[Tracing off — {reason or handle.detail or 'unknown'}.]")

        result = st.session_state.result
        st.caption("Last trace")
        if result is None:
            st.caption(":gray[No roast traced yet this session.]")
        else:
            st.code(_trace_tree(result), language="text", wrap_lines=False)
            st.caption(
                "One `roast.session` root per pitch. The Anthropic instrumentor's "
                "raw LLM spans hang underneath each leaf."
            )


def _telemetry() -> None:
    totals = state.spend_totals()
    runs = state.spend()
    last = runs[-1] if runs else None

    with st.container(border=True):
        st.subheader("Token & credit telemetry", icon=":material/payments:")

        cols = st.columns(2)
        cols[0].metric(
            "Session tokens",
            f"{totals.total_tokens:,}",
            delta=f"{last.total_tokens:,} last roast" if last else None,
            delta_color="off",
            border=True,
            help=f"{totals.input_tokens:,} in / {totals.output_tokens:,} out.",
        )
        cols[1].metric(
            "Session spend",
            costs.eur(totals.usd),
            delta=costs.eur(last.usd) + " last roast" if last else None,
            delta_color="off",
            border=True,
            help=f"${totals.usd:,.4f} at list price.",
        )

        st.progress(
            totals.voucher_used,
            text=(
                f"€{totals.voucher_left_eur:,.2f} of the "
                f"€{costs.voucher_eur():,.0f} voucher left "
                f"({totals.voucher_used * 100:.1f}% spent in this app)"
            ),
        )

        if runs:
            st.dataframe(
                [
                    {
                        "#": i,
                        "model": r.model,
                        "seats": r.seats,
                        "in": r.input_tokens,
                        "out": r.output_tokens,
                        "s": round(r.latency_s, 1),
                        "EUR": round(r.eur, 4),
                    }
                    for i, r in enumerate(runs, start=1)
                ],
                hide_index=True,
                width="stretch",
                height=180,
            )

        # Two assumptions worth saying out loud rather than burying in a docstring.
        st.caption(
            f"List price, no cache discount, converted at "
            f"{costs.eur_per_usd():.2f} EUR/USD. Counts only roasts run in this "
            f"app — CLI demos and `make eval` are billed to the same voucher and "
            f"are invisible here."
        )
        if totals.assumed_prices or not costs.price_for(state.model_id()).confirmed:
            st.caption(
                f":orange[`{state.model_id()}` has no published per-token rate here — "
                f"charged at the Opus tier as an assumption. Confirm it in the "
                f"Console and set `PITCHROAST_PRICING` to make this exact.]"
            )


def _orchestration() -> None:
    with st.container(border=True):
        st.subheader("Model orchestration", icon=":material/tune:")

        # persist_state="session" on every widget in this panel: the Hot Seat
        # does not draw them, and a keyed widget's value is dropped as soon as
        # it stops being rendered. Without it, flipping to the founder view
        # would silently reset the model to the default mid-demo.
        st.selectbox(
            "Model",
            state.MODEL_LABELS,
            index=state.MODEL_LABELS.index(state.DEFAULT_MODEL_LABEL),
            key=state.K_MODEL,
            persist_state="session",
            help="Fable 5.1 while iterating, Opus 5.5 for the stage demo.",
            disabled=st.session_state.running,
        )
        st.selectbox(
            "Reasoning effort",
            state.EFFORTS,
            index=state.EFFORTS.index(state.effort()),
            key=state.K_EFFORT,
            persist_state="session",
            help=(
                "`output_config.effort`. These models reject temperature and "
                "thinking budgets, so this is the only depth dial."
            ),
            disabled=st.session_state.running,
        )

        # Deliberately NOT prefilled with the real key. A password widget's
        # value is still shipped to the browser DOM, and this app gets demoed on
        # a projector and a livestream. Leave it blank; the env key is picked up
        # at call time.
        st.text_input(
            "Anthropic API key override",
            type="password",
            key=state.K_API_KEY,
            persist_state="session",
            placeholder=(
                "Using ANTHROPIC_API_KEY from .env"
                if state.env_key_present()
                else "sk-ant-…"
            ),
            help=(
                "Leave blank to use ANTHROPIC_API_KEY / .env. Never logged, and "
                "never rendered back into the page."
            ),
        )
        if state.env_key_present():
            st.caption(":material/check_circle: Key loaded from the environment.")
        else:
            st.caption(":orange[No ANTHROPIC_API_KEY in the environment.]")

        mood = state.mood()
        st.caption(
            f"Roast intensity {mood.brutality:.2f} — {mood.label}, set by the "
            f"founder's VC mood dial. Interpolated into the system prompt; it is "
            f"not a sampling parameter."
        )


def _concurrency() -> None:
    result = st.session_state.result

    with st.container(border=True):
        st.subheader("Panel concurrency", icon=":material/account_tree:")

        st.multiselect(
            "Partner seats",
            options=state.ALL_PANEL,
            default=state.ALL_PANEL,
            key=state.K_PANEL,
            persist_state="session",
            format_func=lambda pid: (
                f"{PARTNERS_BY_ID[pid].emoji} {PARTNERS_BY_ID[pid].name}"
            ),
            help=(
                "Each seat is one concurrent API call. Drop a seat to demonstrate "
                "the cost of the fan-out; the managing partner always closes."
            ),
            disabled=st.session_state.running,
        )
        seats = state.panel()
        if not seats:
            st.warning("Seat at least one partner.", icon=":material/person_off:")
        else:
            st.caption(
                f"{len(seats)} concurrent partner call"
                f"{'s' if len(seats) != 1 else ''} + 1 synthesis = "
                f"{len(seats) + 1} requests per roast."
            )

        if result is None or not result.partners:
            st.caption(":gray[Run a roast to measure the fan-out.]")
            return

        latencies = [p.latency_s for p in result.partners]
        sequential = sum(latencies)
        slowest = max(latencies)
        cols = st.columns(3)
        cols[0].metric(
            "Partner stage",
            f"{slowest:.1f}s",
            border=True,
            help="The slowest seat — the floor for the parallel stage.",
        )
        cols[1].metric(
            "Sequential equivalent",
            f"{sequential:.1f}s",
            border=True,
            help="What the same calls would have cost one after another.",
        )
        cols[2].metric(
            "Saved by fan-out",
            f"{sequential - slowest:.1f}s",
            border=True,
            help="Exact: sum of the partner latencies minus the slowest one.",
        )
        st.caption(
            f"Partners run in a ThreadPoolExecutor with one worker per seat, with "
            f"the OTEL context re-attached inside each thread so the spans stay "
            f"children of the session root. {SHARK.name} is strictly sequential "
            f"after them — it reads what they filed."
        )


def _deliberation() -> None:
    result = st.session_state.result

    with st.container(border=True):
        st.subheader("Deep deliberation inspector", icon=":material/psychology:")
        if result is None:
            st.caption(":gray[No roast to unpack yet.]")
            return

        traces = [(p.partner.name, p.partner.title, p.thinking) for p in result.partners]
        traces.append((SHARK.name, SHARK.title, result.shark_thinking))
        shown = 0
        for name, title, thinking in traces:
            if not (thinking or "").strip():
                continue
            shown += 1
            with st.expander(f"{name} — {title}", icon=":material/neurology:"):
                st.markdown(thinking)

        if shown:
            st.caption(
                "Summarised `ThinkingBlock` content, requested explicitly with "
                "`thinking={'type': 'adaptive', 'display': 'summarized'}`."
            )
        else:
            st.caption(
                ":gray[No thinking returned. `display` defaults to `omitted` on "
                "this model generation, which yields empty thinking text — "
                "`syndicate.THINKING` asks for summaries, so an empty drawer "
                "means the model chose not to surface any.]"
            )


def _evaluator() -> None:
    result = st.session_state.result

    with st.container(border=True):
        st.subheader("Automated roast evaluator", icon=":material/balance:")
        st.caption(
            "Runs `evaluate.py`'s four LLM judges over the traced spans — "
            "specificity, persona adherence, house rules, pivot value — and "
            "writes the scores back as Phoenix span annotations."
        )

        scoped = st.toggle(
            "Grade only the last roast",
            value=True,
            key="eval_scoped",
            disabled=result is None,
            help="Off grades the newest 100 spans in the project.",
        )
        write_back = st.toggle(
            "Write annotations to Phoenix",
            value=True,
            key="eval_write",
            help="Off scores without annotating (a dry run).",
        )
        st.caption(
            ":orange[Every judgement is a real Anthropic call and spends credits "
            "from the same voucher — they are not counted in the telemetry above.]"
        )

        if st.button(
            "Run evaluator",
            icon=":material/play_arrow:",
            key="eval_btn",
            disabled=st.session_state.running,
        ):
            # Imported here, not at module scope: evaluate pulls in pandas and
            # the Phoenix eval stack, and the Hot Seat must not pay for that.
            import evaluate

            st.session_state.eval_summary = None
            st.session_state.eval_error = None
            session_id = result.session_id if (scoped and result is not None) else None
            try:
                with st.spinner("Judging the roasts…", show_time=True):
                    st.session_state.eval_summary = evaluate.evaluate_project(
                        session_id=session_id,
                        api_key=state.api_key() or None,
                        write=write_back,
                        quiet=True,
                    )
            except evaluate.EvalError as exc:
                st.session_state.eval_error = str(exc)
            except Exception as exc:  # noqa: BLE001 - the evaluator must not kill the demo
                logger.warning("Evaluator failed", exc_info=True)
                st.session_state.eval_error = f"{type(exc).__name__}: {exc}"

        if st.session_state.eval_error:
            st.error(st.session_state.eval_error, icon=":material/error:")

        summary = st.session_state.eval_summary
        if summary:
            st.success(
                f"{summary['spans_graded']} spans graded · "
                f"{summary['written']} annotations written",
                icon=":material/task_alt:",
            )
            means = summary.get("means") or {}
            if means:
                cols = st.columns(len(means))
                for col, (judge, mean) in zip(cols, sorted(means.items()), strict=True):
                    col.metric(
                        judge.replace("_", " "),
                        f"{mean:.2f}",
                        border=True,
                        help="Mean score, 1.00 is best.",
                    )
            annotations = summary.get("annotations")
            if annotations is not None and not annotations.empty:
                st.dataframe(annotations, hide_index=True, width="stretch", height=240)


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


def render() -> None:
    """Draw the observatory. Called once per rerun, by `app.py`."""
    handle, reason = state.tracing()

    header_col, lock_col = st.columns([4, 1], vertical_alignment="center")
    with header_col:
        st.title("Syndicate observatory", anchor=False)
    with lock_col:
        if st.button("🔒 Lock Admin", key="lock_admin_btn", help="Lock the Observatory and return to Hot Seat"):
            st.session_state.admin_authenticated = False
            st.query_params[state.K_MODE] = state.FOUNDER
            st.session_state[state.K_MODE] = state.FOUNDER
            st.rerun()

    st.caption(
        "Operator and judge view. Shares one session with the Founder Hot Seat — "
        "the verdict below was generated there and is not re-run by this page."
    )

    _status_strip(handle, reason)

    left, right = st.columns(2)
    with left:
        _phoenix_hub(handle, reason)
    with right:
        _telemetry()

    left, right = st.columns(2)
    with left:
        _orchestration()
    with right:
        _concurrency()

    _deliberation()
    _evaluator()

    st.divider()
    st.subheader("Verdict under inspection", icon=":material/plagiarism:")
    if st.session_state.setup_error:
        st.error(st.session_state.setup_error, icon=":material/error:")
        st.caption("Raw failure from the last run. The founder view shows only a hint.")
    if st.session_state.result is None:
        st.caption(
            ":gray[Nothing convened yet. Switch to the Founder Hot Seat, run a "
            "pitch, then come back — the verdict persists across the toggle.]"
        )
        return
    board.draw_result(st.session_state.result, technical=True)
