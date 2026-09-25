#!/usr/bin/env python3
"""Offline tests for observability.py and evaluate.py.

No Phoenix server, no Anthropic calls, no network. These cover the two things
that actually break in this layer: tracing being absent (which must degrade to
a no-op rather than raise), and the span-shape contract between the app that
writes traces and the eval runner that reads them back.

Run: .venv/bin/python test_observability.py
"""

from __future__ import annotations

import builtins
import json
import logging
import sys

import evaluate as ev
import observability as obs
import syndicate as s

logging.getLogger("observability").setLevel(logging.CRITICAL)
logging.getLogger("syndicate").setLevel(logging.CRITICAL)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}{f' — {detail}' if detail else ''}")
        FAILURES.append(name)


class FakeSpan:
    """Stands in for an OTEL span so `Span` can be tested without a provider."""

    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.status: str | None = None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def set_status(self, status: object) -> None:
        self.status = str(status)


def _no_phoenix():
    """Context where `import phoenix` raises, as on a bare (non-[obs]) install."""

    class Blocker:
        def __enter__(self):
            self.real = builtins.__import__

            def fake(name, *args, **kwargs):
                if name == "phoenix" or name.startswith(("phoenix.", "openinference")):
                    raise ImportError(f"No module named {name!r}")
                return self.real(name, *args, **kwargs)

            builtins.__import__ = fake
            return self

        def __exit__(self, *exc):
            builtins.__import__ = self.real
            return False

    return Blocker()


def test_config() -> None:
    print("\nProject configuration")
    import os

    saved = os.environ.pop("PHOENIX_PROJECT_NAME", None)
    try:
        check("defaults to the project name", obs.project_name() == obs.DEFAULT_PROJECT)
        os.environ["PHOENIX_PROJECT_NAME"] = "  custom-project  "
        check("env override wins and is stripped", obs.project_name() == "custom-project")
        os.environ["PHOENIX_PROJECT_NAME"] = "   "
        check("blank env falls back to default", obs.project_name() == obs.DEFAULT_PROJECT)
    finally:
        os.environ.pop("PHOENIX_PROJECT_NAME", None)
        if saved is not None:
            os.environ["PHOENIX_PROJECT_NAME"] = saved


def test_degrades_without_phoenix() -> None:
    print("\nDegradation — Phoenix not installed")
    obs.reset()
    try:
        with _no_phoenix():
            tracing = obs.setup_observability()
        check("returns a Tracing instead of raising", isinstance(tracing, obs.Tracing))
        check("reports itself disabled", not tracing.enabled and not tracing)
        check("still knows the project name", tracing.project == obs.project_name())
        check("explains why", "not installed" in tracing.detail)
        check("no URL to link to", tracing.url is None and obs.trace_url(tracing) is None)

        # The whole point: callers never branch on this.
        with obs.span("anything", input_value="x", session_id="s") as span:
            check("span() yields the null span", span is obs.NULL_SPAN)
            span.set("k", "v")
            span.set_output({"a": 1})
            span.set_tokens(1, 2)
            span.set_metadata(x=1)
            span.failed("nope")
        check("null span absorbs every call", True)

        check("capture_context returns None", obs.capture_context() is None)
        with obs.use_context(None):
            pass
        check("use_context(None) is a no-op", True)
    finally:
        obs.reset()


def test_idempotent() -> None:
    print("\nIdempotency — reruns must not launch a second Phoenix")
    # app.py calls this from @st.cache_resource and run_demo.py once per run; a
    # second call has to hit cached state rather than start another server.
    obs.reset()
    try:
        with _no_phoenix():
            first = obs.setup_observability()
            second = obs.setup_observability()
        check("same handle returned", first is second)
        check("status() exposes it without re-running setup", obs.status() is first)
        obs.reset()
        check("reset() clears the cache", obs.status() is not first)
        check("status() before setup reports uninitialised", not obs.status().enabled)
    finally:
        obs.reset()


def test_span_attributes() -> None:
    print("\nSpan attributes")
    raw = FakeSpan()
    span = obs.Span(raw)
    check("live span reports live", span.live and not obs.NULL_SPAN.live)

    span.set("str.key", "plain")
    span.set("int.key", 7)
    span.set("bool.key", True)
    span.set("none.key", None)
    check("strings pass through", raw.attributes["str.key"] == "plain")
    check("numbers stay numeric", raw.attributes["int.key"] == 7)
    check("bools stay bool", raw.attributes["bool.key"] is True)
    check("None is dropped, not stringified", "none.key" not in raw.attributes)

    span.set_output({"critique": "Your TAM includes tap water.", "moat_score": 1})
    payload = json.loads(raw.attributes["output.value"])
    check("dict output is JSON", payload["critique"] == "Your TAM includes tap water.")
    check("mime type marked as JSON", raw.attributes["output.mime_type"] == "application/json")

    span.set_output("just a string")
    check("string output is not re-encoded", raw.attributes["output.value"] == "just a string")

    span.set_tokens(100, 250)
    check("tokens total correctly", raw.attributes["llm.token_count.total"] == 350)

    span.set_metadata(partner_id="marc", error=None)
    meta = json.loads(raw.attributes["metadata"])
    check("metadata drops None values", meta == {"partner_id": "marc"})

    span.set_metadata(everything=None)
    check("all-None metadata writes nothing new", json.loads(raw.attributes["metadata"]) == meta)


def test_session_id_on_result() -> None:
    print("\nSession id threading")
    import test_syndicate as ts

    original = s._call
    s._call = ts.fake_call_factory()
    try:
        auto = s.convene("A pitch.", api_key="k")
        check("a session id is generated", bool(auto.session_id) and len(auto.session_id) == 16)
        given = s.convene("A pitch.", api_key="k", session_id="fixed-session")
        check("an explicit session id is kept", given.session_id == "fixed-session")
        check("two runs get different ids", auto.session_id != s.convene("x", api_key="k").session_id)
    finally:
        s._call = original


def test_setup_observability_contract() -> None:
    print("\nsyndicate.setup_observability contract")
    obs.reset()
    try:
        with _no_phoenix():
            url = s.setup_observability()
        check("returns str | None, never a Tracing", url is None or isinstance(url, str))
        check("JSON-serialisable for run_demo --json", json.dumps({"phoenix_url": url}) is not None)
    finally:
        obs.reset()


def _spans_frame():
    """A DataFrame shaped exactly like Phoenix's, built from known values."""
    import pandas as pd

    rows = [
        {
            "name": obs.SESSION_SPAN,
            "start_time": 3,
            "attributes.input.value": "An oat milk blockchain.",
            "attributes.output.value": json.dumps(
                {"the_pivot": "Sell the telemetry.", "closing_line": "Good day.", "funded": False}
            ),
            "attributes.metadata": {"model": "claude-fable-5-1"},
            "attributes.session.id": "sess-1",
        },
        {
            "name": obs.PARTNER_SPAN,
            "start_time": 2,
            "attributes.input.value": "An oat milk blockchain.",
            "attributes.output.value": json.dumps(
                {"critique": "Your TAM includes tap water.", "zinger": "A burn rate with a logo."}
            ),
            "attributes.metadata": {
                "partner_id": "marc",
                "partner_name": "Marc Low-res",
                "partner_focus": "Market delusions",
            },
            "attributes.session.id": "sess-1",
        },
        {  # recused partner: no critique, must be skipped
            "name": obs.PARTNER_SPAN,
            "start_time": 1,
            "attributes.input.value": "An oat milk blockchain.",
            "attributes.output.value": None,
            "attributes.metadata": {"partner_id": "karen"},
            "attributes.session.id": "sess-1",
        },
        {  # an unrelated span from the raw instrumentor, must be filtered out
            "name": "messages.parse",
            "start_time": 0,
            "attributes.input.value": "raw",
            "attributes.output.value": None,
            "attributes.metadata": None,
            "attributes.session.id": "sess-1",
        },
    ]
    return pd.DataFrame(rows, index=[f"span-{i}" for i in range(len(rows))])


def test_build_frames() -> None:
    print("\nEval input — span to gradeable row")
    agents, sessions = ev.build_frames(_spans_frame())

    check("one gradeable agent row", len(agents) == 1, f"got {len(agents)}")
    check("recused partner skipped", "karen" not in set(agents["partner"]))
    row = agents.iloc[0]
    check("span_id preserved for write-back", row["span_id"] == "span-1")
    check("critique carried over", "tap water" in row["critique"])
    check("zinger folded into the critique", "burn rate with a logo" in row["critique"].lower())
    check("remit read from span metadata", row["remit"] == "Market delusions")
    check("partner name resolved", row["partner"] == "Marc Low-res")

    check("one session row", len(sessions) == 1, f"got {len(sessions)}")
    check("pivot extracted", sessions.iloc[0]["pivot"] == "Sell the telemetry.")
    check("session id carried", sessions.iloc[0]["session_id"] == "sess-1")


def test_remit_fallback() -> None:
    print("\nRemit fallback — spans written before partner_focus existed")
    check("known id resolves from the live personas", ev._remit("marc") == s.PARTNERS[0].focus)
    check("unknown id gets a usable default", bool(ev._remit("nobody")))


def test_to_annotations() -> None:
    print("\nEval output — scores to Phoenix annotations")
    import pandas as pd

    scored = pd.DataFrame(
        [
            {
                "span_id": "span-1",
                "roast_specificity_score": json.dumps(
                    {"name": "roast_specificity", "label": "specific", "score": 1.0,
                     "explanation": "Quotes the TAM."}
                ),
                # The judge errored on this one — must not become a null annotation.
                "house_rules_score": json.dumps(
                    {"name": "house_rules", "label": None, "score": None, "explanation": "refusal"}
                ),
            }
        ]
    )
    annotations = ev.to_annotations(scored)
    check("only scored rows survive", len(annotations) == 1, f"got {len(annotations)}")
    row = annotations.iloc[0]
    check("annotation name from the Score", row["annotation_name"] == "roast_specificity")
    check("label written", row["label"] == "specific")
    check("numeric score written", row["score"] == 1.0)
    check("explanation written", "TAM" in row["explanation"])

    check("empty input yields no annotations", ev.to_annotations(pd.DataFrame([{"span_id": "x"}])).empty)
    check("means of an empty frame is empty", ev._means(pd.DataFrame()) == {})
    check("means averages by name", ev._means(annotations) == {"roast_specificity": 1.0})


def test_verdict_schema() -> None:
    print("\nJudge schema")
    import pydantic

    schema = ev._verdict_schema(ev._SPEC_CHOICES)
    ok = schema(label="specific", explanation="because")
    check("valid label accepted", ok.label == "specific")
    try:
        schema(label="wildly_invented", explanation="because")
        check("invalid label rejected", False, "no ValidationError raised")
    except pydantic.ValidationError:
        check("invalid label rejected", True)
    fields = schema.model_json_schema()["properties"]
    check("label is an enum in the JSON schema", "enum" in json.dumps(fields))
    check("every choice maps to a number", all(
        isinstance(v, float) for v in ev._SPEC_CHOICES.values()
    ))


def test_eval_errors() -> None:
    print("\nEval error messages")
    import pandas as pd

    # Every failure mode below must be an EvalError with a fix in the text,
    # not a stack trace at 20:30.
    try:
        ev.fetch_spans(base_url="http://127.0.0.1:1", limit=1)
        check("unreachable Phoenix is an EvalError", False, "no error raised")
    except ev.EvalError as exc:
        check("unreachable Phoenix is an EvalError", "Could not read project" in str(exc))
    except Exception as exc:  # noqa: BLE001
        check("unreachable Phoenix is an EvalError", False, f"got {type(exc).__name__}: {exc}")

    empty_agents, empty_sessions = ev.build_frames(pd.DataFrame(columns=["name"]))
    check("empty spans yield empty frames", empty_agents.empty and empty_sessions.empty)
    check("run_judges passes empty frames straight through",
          ev.run_judges(empty_agents, [], quiet=True).empty)

    import os

    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        ev._judge_client(None)
        check("missing key is an EvalError", False, "no error raised")
    except ev.EvalError as exc:
        check("missing key is an EvalError", "ANTHROPIC_API_KEY" in str(exc))
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_cli_args() -> None:
    print("\nEval CLI")
    args = ev._parse_args([])
    check("defaults to the configured project", args.project is None and args.limit == 100)
    check("judge defaults to the cheap model", args.judge_model == ev.DEFAULT_JUDGE_MODEL)
    args = ev._parse_args(["--session", "abc", "--limit", "5", "--dry-run", "--json"])
    check("session filter parsed", args.session == "abc" and args.limit == 5)
    check("dry-run and json parsed", args.dry_run and args.json)


def main() -> int:
    test_config()
    test_degrades_without_phoenix()
    test_idempotent()
    test_span_attributes()
    test_session_id_on_result()
    test_setup_observability_contract()
    test_build_frames()
    test_remit_fallback()
    test_to_annotations()
    test_verdict_schema()
    test_eval_errors()
    test_cli_args()

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} check(s) failed: {', '.join(FAILURES)}\n")
        return 1
    print("✅ All observability + eval checks passed (no Phoenix, no API calls).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
