"""Everything that has to survive a rerun, plus the one process-wide bootstrap.

Both entry points — the Founder Hot Seat (`founder.py`) and the Syndicate
Observatory (`admin.py`) — read and write through here, which is what
makes flipping between them lossless: the verdict, the spend log and every
operator setting live in session state, not in whichever view happened to draw
the widget.

The settings the Observatory owns (model, effort, panel, API key) are still
needed by a run started from the Hot Seat, where those widgets are not on the
page at all. A keyed widget's value is normally dropped the moment it stops
being rendered, so every one of them is declared `persist_state="session"` at
its call site and read here through `.get(...)` with the same fallback the
widget uses. Do **not** `setdefault` those keys: writing them ourselves and
also passing `index=` / `default=` to the widget is what triggers Streamlit's
"mixing value and session state" warning.

Security note, because the mode switch looks like one and is not: the split is
a UX boundary, not an authorisation boundary. `?mode=admin` is a query
parameter anyone can type, and everything the Observatory shows (traces, token
counts, model ids) is local, non-secret operational data. The API key field is
write-only — it is never rendered back into the page.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass

import streamlit as st

import costs
import observability as obs
from syndicate import DEFAULT_EFFORT, DEFAULT_MODEL, MODELS, PARTNERS

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

FOUNDER = "founder"
ADMIN = "admin"

# Order matters: the first entry is the default, and `bind="query-params"`
# drops the parameter from the URL whenever the value equals the default. So
# ?mode=admin is a shareable link and plain / is the founder experience.
MODE_LABELS: dict[str, str] = {
    FOUNDER: "🎯 Founder hot seat",
    ADMIN: "🔬 Syndicate observatory",
}

K_MODE = "mode"

# --------------------------------------------------------------------------
# Operator settings (Observatory widgets, read from anywhere)
# --------------------------------------------------------------------------

K_MODEL = "cfg_model_label"
K_EFFORT = "cfg_effort"
K_PANEL = "cfg_panel"
K_API_KEY = "cfg_api_key"
K_MOOD = "cfg_mood"

MODEL_LABELS: list[str] = list(MODELS)
DEFAULT_MODEL_LABEL: str = next(
    (label for label, model in MODELS.items() if model == DEFAULT_MODEL),
    MODEL_LABELS[0],
)

# `output_config.effort` — the only reasoning-depth dial these models accept.
EFFORTS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")

ALL_PANEL: list[str] = [p.id for p in PARTNERS]


@dataclass(frozen=True)
class Mood:
    """One notch on the founder-facing brutality dial.

    `brutality` lands inside a band of `syndicate._brutality_clause`, so each
    notch genuinely changes the prompt text rather than nudging a number the
    model never sees.
    """

    label: str
    brutality: float
    blurb: str


MOODS: tuple[Mood, ...] = (
    Mood("😇 Friendly angel", 0.35, "Dry, understated, lets the facts do the damage."),
    Mood("🦈 Sand Hill shark", 0.85, "Brutal. No diplomatic cushioning whatsoever."),
    Mood("🔥 Scorched earth", 1.00, "Maximum. Reconsider your life choices."),
)
DEFAULT_MOOD = MOODS[1]
MOODS_BY_LABEL: dict[str, Mood] = {m.label: m for m in MOODS}


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------


def init() -> None:
    """Create the non-widget keys. Safe to call on every rerun."""
    # Seeded from the URL exactly once per session, before the switch renders.
    # After that the widget owns it and `sync_mode_to_url` writes it back out.
    st.session_state.setdefault(K_MODE, mode_from_url())
    st.session_state.setdefault("pitch_text", "")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("setup_error", None)
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("spend", [])
    st.session_state.setdefault("eval_summary", None)
    st.session_state.setdefault("eval_error", None)


def mode() -> str:
    """The active view. Unknown values from the URL fall back to the founder."""
    value = st.session_state.get(K_MODE)
    return value if value in MODE_LABELS else FOUNDER


def mode_from_url() -> str:
    """Read `?mode=` once, at the top of the first script run of a session."""
    raw = (st.query_params.get(K_MODE) or "").strip().lower()
    return raw if raw in MODE_LABELS else FOUNDER


def sync_mode_to_url() -> None:
    """`on_change` for the mode switch: mirror the new view into the URL.

    Runs before the rerun renders, so the parameter is already correct by the
    time the page is drawn — no second rerun, and no risk of the
    "modified after widget creation" exception.
    """
    st.session_state[K_MODE] = mode()
    st.query_params[K_MODE] = st.session_state[K_MODE]


def model_label() -> str:
    return st.session_state.get(K_MODEL) or DEFAULT_MODEL_LABEL


def model_id() -> str:
    return MODELS.get(model_label(), DEFAULT_MODEL)


def effort() -> str:
    value = st.session_state.get(K_EFFORT) or DEFAULT_EFFORT
    return value if value in EFFORTS else DEFAULT_EFFORT


def panel() -> list[str]:
    """Seated partner ids, filtered back through the real roster.

    Widget options are a client-side convenience, not a guarantee: the value
    that arrives in session state is whatever the browser sent. `convene`
    raises on an unknown id, so drop anything that is not a real partner
    instead of letting a doctored request take the run down.
    """
    seated = st.session_state.get(K_PANEL)
    if seated is None:
        return list(ALL_PANEL)
    return [pid for pid in ALL_PANEL if pid in set(seated)]


def mood() -> Mood:
    return MOODS_BY_LABEL.get(st.session_state.get(K_MOOD, ""), DEFAULT_MOOD)


def brutality() -> float:
    return mood().brutality


def api_key() -> str:
    """The key a run should use: the Observatory override, else the environment.

    The override is never rendered back into the page — the widget is a blank
    password field every run, and this is the only reader.
    """
    typed = (st.session_state.get(K_API_KEY) or "").strip()
    return typed or (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def env_key_present() -> bool:
    return bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())


def pitch() -> str:
    return (st.session_state.get("pitch_text") or "").strip()


def clear_pitch() -> None:
    """Reset the pitch and the verdict. Leaves the spend log alone."""
    st.session_state.pitch_text = ""
    st.session_state.preset_choice = None
    st.session_state.result = None
    st.session_state.setup_error = None


# --------------------------------------------------------------------------
# Spend log
# --------------------------------------------------------------------------


def record_spend(result) -> None:
    """Append one costed run. Called once, by the runner, per convene()."""
    st.session_state.spend = [*st.session_state.get("spend", []), costs.cost_of(result)]


def spend() -> list[costs.RunCost]:
    return list(st.session_state.get("spend", []))


def spend_totals() -> costs.Totals:
    return costs.totals(spend())


# --------------------------------------------------------------------------
# Observability bootstrap
# --------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def tracing() -> tuple[obs.Tracing, str]:
    """Start local Phoenix once per server process.

    Returns `(handle, reason_it_is_off)`. Tracing runs in **both** modes — the
    founder never sees Phoenix, but their roast still has to land in it, or the
    Observatory has nothing to show after the toggle.

    When Phoenix cannot bind its port it dumps a multi-screen uvicorn traceback
    to stderr, so on stage the operator sees a wall of red while the sidebar
    says one quiet line. Capture that noise and surface the actual reason.
    """
    for name in ("uvicorn", "uvicorn.error", "phoenix", "phoenix.server"):
        logging.getLogger(name).setLevel(logging.CRITICAL)

    # Must redirect at the file-descriptor level, not with redirect_stderr:
    # the loudest line ("Failed to add port ... Address already in use") is
    # written by grpc's C++ layer straight to fd 2, and redirect_stderr only
    # rebinds Python's sys.stderr object. Verified: a raw os.write(2, ...) is
    # invisible to redirect_stderr.
    with tempfile.TemporaryFile(mode="w+") as sink:
        saved_fd = os.dup(2)
        try:
            os.dup2(sink.fileno(), 2)
            handle = obs.setup_observability()
        finally:
            os.dup2(saved_fd, 2)
            os.close(saved_fd)
        sink.seek(0)
        captured = sink.read()

    # This also swallows genuine crashes, so keep the text retrievable.
    if captured.strip():
        logger.debug("Phoenix startup stderr:\n%s", captured)

    if handle.enabled:
        return handle, ""

    if "Address already in use" in captured or "STARTUP_FAILURE" in captured:
        reason = "port already in use — another app or Phoenix instance has it"
    elif "No module named" in captured or "ModuleNotFoundError" in captured:
        reason = "not installed — reinstall with the [obs] extra"
    else:
        reason = handle.detail or "could not start"
    logger.info("Phoenix tracing off: %s", reason)
    return handle, reason
