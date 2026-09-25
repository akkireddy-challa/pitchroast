"""Phoenix observability for PitchRoast — named project, session traces, evals.

Three jobs, in order of how much they matter on stage:

1. **A named project.** Traces used to land in Phoenix's `default` project mixed
   with anything else running locally. Every run now goes to a project named by
   `PHOENIX_PROJECT_NAME` (default `pitchroast-syndicate`), created up front so
   it is visible in the UI before the first pitch is submitted.
2. **A trace shape you can evaluate.** The raw Anthropic instrumentor emits four
   unrelated LLM spans per run. We wrap them: one `roast.session` root span per
   `convene()`, with one `roast.partner` / `roast.shark` child per agent, each
   carrying `input.value` / `output.value`. `evaluate.py` grades those spans.
3. **Never breaking the demo.** Every entry point degrades to a no-op if Phoenix
   is not installed, the port is taken, or the collector is unreachable.

Nothing here imports `syndicate`, so `syndicate` can import it freely.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PROJECT = "pitchroast-syndicate"
PROJECT_DESCRIPTION = (
    "Autonomous VC syndicate. One roast.session trace per pitch; "
    "roast.partner / roast.shark children carry the critiques that evaluate.py grades."
)

# Span names. `evaluate.py` filters on these, so they are part of the contract
# between the app and the eval runner — change them in both places or not at all.
SESSION_SPAN = "roast.session"
PARTNER_SPAN = "roast.partner"
SHARK_SPAN = "roast.shark"

TRACER_NAME = "pitchroast"


def project_name() -> str:
    """The Phoenix project traces are written to."""
    return (os.getenv("PHOENIX_PROJECT_NAME") or "").strip() or DEFAULT_PROJECT


def collector_endpoint() -> str | None:
    """An already-running Phoenix to send to, instead of launching one."""
    return (os.getenv("PHOENIX_COLLECTOR_ENDPOINT") or "").strip() or None


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------


@dataclass
class Tracing:
    """What came up. `enabled` is False whenever spans are going nowhere."""

    enabled: bool = False
    url: str | None = None
    project: str = ""
    launched: bool = False  # True if we started the Phoenix server ourselves
    detail: str = ""

    def __bool__(self) -> bool:
        return self.enabled


_STATE: Tracing | None = None


def setup_observability(project: str | None = None) -> Tracing:
    """Bring up Phoenix, register a named project, instrument Anthropic.

    Idempotent: Streamlit reruns and repeated CLI calls get the same session
    back rather than launching a second server on a second port.
    """
    global _STATE
    if _STATE is not None:
        return _STATE

    name = project or project_name()
    try:
        import phoenix as px
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
    except ImportError as exc:
        # Phoenix is an optional extra (`pip install -e ".[obs]"`). A bare
        # install has none of this, and that is a supported way to run.
        logger.info("Phoenix not installed, tracing disabled: %s", exc)
        _STATE = Tracing(project=name, detail=f"phoenix not installed ({exc})")
        return _STATE

    try:
        existing = collector_endpoint()
        if existing:
            base, launched = existing.rstrip("/"), False
        else:
            session = px.launch_app(run_in_thread=True)
            if session is None:
                # launch_app logs its own failure and returns None rather than
                # raising. Overwhelmingly this is "the port is already taken" —
                # i.e. a Phoenix from an earlier `make app` is still up. Use it.
                base = _adopt_running_phoenix()
                if base is None:
                    raise RuntimeError(
                        "phoenix.launch_app() failed and nothing is serving Phoenix on "
                        f"{_default_base()}. Free the port, or point "
                        "PHOENIX_COLLECTOR_ENDPOINT at a running instance."
                    )
                launched = False
                logger.info("Adopted the Phoenix already running at %s", base)
            else:
                base, launched = session.url.rstrip("/"), True
            # The Phoenix client reads this; launch_app picks a free port when
            # 6006 is taken, so publish whatever it actually settled on.
            os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = base

        ensure_project(name, base_url=base)
        provider = _tracer_provider(name, base)
        AnthropicInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True)

        _STATE = Tracing(enabled=True, url=base, project=name, launched=launched)
        logger.info("Phoenix tracing live at %s (project %r)", base, name)
    except Exception as exc:  # noqa: BLE001 - tracing must never break the demo
        logger.warning("Phoenix failed to start: %s", exc, exc_info=True)
        _STATE = Tracing(project=name, detail=f"{type(exc).__name__}: {exc}")
    return _STATE


def _default_base() -> str:
    port = (os.getenv("PHOENIX_PORT") or "6006").strip() or "6006"
    return f"http://localhost:{port}"


def _adopt_running_phoenix() -> str | None:
    """Is a Phoenix already serving on the default port? Return its base URL."""
    base = _default_base()
    try:
        import urllib.request

        with urllib.request.urlopen(f"{base}/healthz", timeout=2) as response:
            if response.status == 200:
                return base
    except Exception:  # noqa: BLE001 - nothing there, or not Phoenix
        return None
    return None


def _tracer_provider(name: str, base: str) -> Any:
    """Build the provider by hand instead of calling `phoenix.otel.register()`.

    register() is the documented path, but arize-phoenix-otel 0.17.1 reads a
    private `exporter._headers` that opentelemetry-exporter-otlp-proto-http
    1.45 no longer defines, so it raises AttributeError before returning. This
    does the same three things — resource-tag the project, batch, export — with
    no coupling to that private attribute.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from phoenix.otel import PROJECT_NAME, HTTPSpanExporter

    provider = TracerProvider(resource=Resource.create({PROJECT_NAME: name}))
    provider.add_span_processor(
        BatchSpanProcessor(HTTPSpanExporter(endpoint=f"{base}/v1/traces"))
    )
    # Global, so `trace.get_tracer()` in `_tracer()` and any other
    # OTEL-instrumented library in-process both land in the same project.
    trace.set_tracer_provider(provider)
    return provider


def ensure_project(name: str, *, base_url: str | None = None) -> bool:
    """Create the project if it does not exist yet. True if it exists after this.

    Phoenix would auto-create it on the first span anyway; doing it explicitly
    means the project is in the UI (with a description) before anyone pitches.
    """
    try:
        from phoenix.client import Client

        client = Client(base_url=base_url or collector_endpoint())
        try:
            client.projects.get(project_name=name)
            return True
        except Exception:  # noqa: BLE001 - "not found" has no dedicated type here
            client.projects.create(name=name, description=PROJECT_DESCRIPTION)
            logger.info("Created Phoenix project %r", name)
            return True
    except Exception as exc:  # noqa: BLE001
        # A race with another process, or an older server without the projects
        # API. Spans still land — Phoenix creates the project on ingest.
        logger.info("Could not pre-create project %r (%s); ingest will create it", name, exc)
        return False


def trace_url(tracing: Tracing | None) -> str | None:
    """Deep link to the project's trace list, not just the Phoenix home page."""
    if not tracing or not tracing.url:
        return None
    return f"{tracing.url}/projects"


def status() -> Tracing:
    """Current tracing state without starting anything."""
    # Explicit `is None`, not `or`: a disabled Tracing is falsy by design, so
    # `_STATE or ...` would discard the real (disabled) state and report
    # "not initialised" for a setup that ran and failed.
    return Tracing(project=project_name(), detail="not initialised") if _STATE is None else _STATE


def reset() -> None:
    """Drop cached state. Tests only — does not stop a running Phoenix."""
    global _STATE
    _STATE = None


# --------------------------------------------------------------------------
# Spans
# --------------------------------------------------------------------------


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def _flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(value)


class Span:
    """Thin wrapper over an OTEL span that is safe when tracing is off.

    Every method is a no-op on the null span, so callers never branch on
    whether Phoenix came up.
    """

    __slots__ = ("_span",)

    def __init__(self, span: Any = None):
        self._span = span

    @property
    def live(self) -> bool:
        return self._span is not None

    def set(self, key: str, value: Any) -> None:
        if self._span is None or value is None:
            return
        try:
            self._span.set_attribute(key, value if isinstance(value, (int, float, bool)) else _flatten(value))
        except Exception:  # noqa: BLE001
            logger.debug("span.set_attribute failed for %s", key, exc_info=True)

    def set_output(self, value: Any) -> None:
        self.set("output.value", value)
        if not isinstance(value, str):
            self.set("output.mime_type", "application/json")

    def set_metadata(self, **values: Any) -> None:
        clean = {k: v for k, v in values.items() if v is not None}
        if clean:
            self.set("metadata", clean)

    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.set("llm.token_count.prompt", int(input_tokens))
        self.set("llm.token_count.completion", int(output_tokens))
        self.set("llm.token_count.total", int(input_tokens) + int(output_tokens))

    def failed(self, reason: str) -> None:
        """Mark the span red in Phoenix so failed runs are filterable."""
        if self._span is None:
            return
        try:
            from opentelemetry.trace import Status, StatusCode

            self._span.set_status(Status(StatusCode.ERROR, reason))
        except Exception:  # noqa: BLE001
            logger.debug("span.set_status failed", exc_info=True)


NULL_SPAN = Span()


def _tracer() -> Any:
    if _STATE is None or not _STATE.enabled:
        return None
    try:
        from opentelemetry import trace

        return trace.get_tracer(TRACER_NAME)
    except Exception:  # noqa: BLE001
        return None


@contextlib.contextmanager
def span(
    name: str,
    *,
    kind: str = "CHAIN",
    input_value: Any = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Span]:
    """Open an OpenInference-annotated span. Yields NULL_SPAN when tracing is off."""
    tracer = _tracer()
    if tracer is None:
        yield NULL_SPAN
        return

    try:
        cm = tracer.start_as_current_span(name)
    except Exception:  # noqa: BLE001
        yield NULL_SPAN
        return

    with cm as raw:
        s = Span(raw)
        s.set("openinference.span.kind", kind)
        if input_value is not None:
            s.set("input.value", input_value)
            if not isinstance(input_value, str):
                s.set("input.mime_type", "application/json")
        if session_id:
            s.set("session.id", session_id)
        if tags:
            s.set("tag.tags", _flatten(tags))
        if metadata:
            s.set_metadata(**metadata)
        try:
            yield s
        except Exception as exc:
            s.failed(f"{type(exc).__name__}: {exc}")
            raise


# --------------------------------------------------------------------------
# Cross-thread context
# --------------------------------------------------------------------------
# The three partners run in a ThreadPoolExecutor. OTEL context is thread-local,
# so without this their spans become orphan roots instead of children of the
# session span — and the eval runner loses the link back to the pitch.


def capture_context() -> Any:
    """Snapshot the current OTEL context, to re-attach inside a worker thread."""
    if _STATE is None or not _STATE.enabled:
        return None
    try:
        from opentelemetry import context as otel_context

        return otel_context.get_current()
    except Exception:  # noqa: BLE001
        return None


@contextlib.contextmanager
def use_context(captured: Any) -> Iterator[None]:
    """Re-attach a context captured by `capture_context` in another thread."""
    if captured is None:
        yield
        return
    try:
        from opentelemetry import context as otel_context
    except Exception:  # noqa: BLE001
        yield
        return
    token = otel_context.attach(captured)
    try:
        yield
    finally:
        with contextlib.suppress(Exception):
            otel_context.detach(token)
