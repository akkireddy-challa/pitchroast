#!/usr/bin/env python3
"""Offline tests for the presentation layer in `ui.py`.

These render real Streamlit scripts through `streamlit.testing.v1.AppTest`, in
process. Nothing here touches the Anthropic API, starts Phoenix, or needs a
key — `ui.py` is pure presentation and every partner verdict below is a literal.

The case that earns this file is the lifecycle one. A partner's slot is
re-rendered in place as waiting -> running -> done within a single script run,
and Streamlit raises StreamlitDuplicateElementKey if the same key is registered
twice in one run, even when the second render replaces the first inside the
same `st.empty()`. That traceback would take the demo down, and any future edit
to `draw_partner` or to the key helpers could reintroduce it.

Run: .venv/bin/python test_ui.py
"""

from __future__ import annotations

import re
import sys

from streamlit.testing.v1 import AppTest

import ui
from syndicate import ALL_PARTNERS, PARTNERS

FAILURES: list[str] = []

# Generous: the first AppTest run imports streamlit, syndicate and anthropic.
TIMEOUT = 90


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}{f' — {detail}' if detail else ''}")
        FAILURES.append(name)


# Appended to every rendered script. A script that fails to compile produces no
# elements AND may leave `at.exception` empty, so "no exception" alone is not
# evidence that anything ran — an early version of this file reported a
# SyntaxError-ed lifecycle test as passing. Reaching the sentinel is the proof.
SENTINEL = "__UI_TEST_RENDER_OK__"


def render(script: str) -> AppTest:
    """Run a script, with a trailing sentinel proving it reached the end."""
    at = AppTest.from_string(
        f'{script}\nimport streamlit as _st\n_st.write("{SENTINEL}")\n',
        default_timeout=TIMEOUT,
    )
    return at.run()


def ran(at: AppTest) -> bool:
    """True only if the script compiled, raised nothing, and ran to completion."""
    if at.exception:
        return False
    return any(SENTINEL in m.value for m in at.markdown)


def why(at: AppTest) -> str:
    if at.exception:
        return str(at.exception)[:160]
    return "script did not reach the end (compile error?)"


def stylesheet(at: AppTest) -> str:
    """The one <style> block emitted by `inject_flair`."""
    blocks = [b.value for b in at.get("html") if b.value.lstrip().startswith("<style>")]
    return blocks[0] if blocks else ""


# A verdict whose text is hostile on purpose. The audience types the pitches,
# so model output is attacker-influenced and must never reach an HTML string.
# Embedded with repr() rather than interpolated raw: the payload contains the
# quote characters that would otherwise terminate the generated string literal.
XSS = '<img src=x onerror="alert(1)">'
CRITIQUE = f"CRITIQUE_SENTINEL {XSS}"
ZINGER = f"ZINGER_SENTINEL {XSS}"

_FAKE_VERDICT = f"""
import streamlit as st
import ui
from syndicate import PARTNERS, PartnerResult, PartnerVerdict

def verdict():
    return PartnerVerdict(
        critique={CRITIQUE!r},
        delusion_index=94,
        moat_score=1,
        runway_months=3,
        zinger={ZINGER!r},
    )
"""


def main() -> int:
    print("\nKey namespacing")
    statuses = ("waiting", "running", "done")
    keys = [ui.slot_key(PARTNERS[0], s) for s in statuses]
    check("a status maps to one key each", len(set(keys)) == 3, str(keys))
    check("done is the card namespace", ui.slot_key(PARTNERS[0], "done") == "partner_marc")
    check("waiting is its own namespace", ui.slot_key(PARTNERS[0], "waiting") == "waiting_marc")
    check("running is its own namespace", ui.slot_key(PARTNERS[0], "running") == "running_marc")
    check("card_key agrees with slot_key", ui.card_key(PARTNERS[0]) == keys[2])
    check("unknown status falls back to card", ui.slot_key(PARTNERS[0], "bogus") == "partner_marc")
    all_keys = {ui.slot_key(p, s) for p in ALL_PARTNERS for s in statuses}
    check("keys unique across committee", len(all_keys) == len(ALL_PARTNERS) * 3)

    print("\nStylesheet")
    at = render("import ui\nui.inject_flair()\n")
    check("renders without exception", ran(at), why(at))
    css = stylesheet(at)
    check("a stylesheet is emitted", bool(css))

    # SPEC.md §2 names these five as product requirements.
    # Matched up to the brace, not as a bare substring: "@keyframes ledBlink"
    # is also a prefix of "@keyframes ledBlinkBROKEN", so a substring test
    # passes against a renamed animation. Verified by injecting that rename.
    for name in ("slideUpFade", "pulseGlow", "flameFlicker", "ledBlink"):
        declared = re.search(rf"@keyframes\s+{re.escape(name)}\s*\{{", css) is not None
        used = re.search(rf"animation:\s*{re.escape(name)}\b", css) is not None
        check(f"{name} keyframes declared", declared)
        check(f"{name} is actually applied", used)
    check("hoverElevation is -4px", "translateY(-4px)" in css)
    check("glassmorphism surface", "backdrop-filter: blur(12px)" in css)
    check("reduced-motion fallback", "prefers-reduced-motion" in css)

    print("\nSelector integrity")
    # Every .st-key-* the stylesheet targets must be a key slot_key can emit.
    targeted = set(re.findall(r"\.st-key-([A-Za-z0-9_]+)\s*\{", css))
    unknown = targeted - all_keys
    check("no selector targets an unreachable key", not unknown, f"orphans: {sorted(unknown)}")
    check("every partner is styled", all_keys <= targeted | {k for k in all_keys if k in css})

    # A comma-separated scope must carry the suffix on EVERY part; appending to
    # the raw string silently drops all but the last selector.
    for ns in ("partner_", "waiting_", "running_"):
        check(
            f"{ns} carries the :hover suffix",
            f'[class*="st-key-{ns}"]:hover' in css,
        )
        check(
            f"{ns} carries the ::before suffix",
            f'[class*="st-key-{ns}"]::before' in css,
        )

    print("\nInjection safety")
    at = render(
        _FAKE_VERDICT
        + "\nui.inject_flair()\n"
        + "ui.partner_card(PartnerResult(partner=PARTNERS[0], verdict=verdict()))\n"
    )
    check("card renders without exception", ran(at), why(at))
    html_blobs = " ".join(b.value for b in at.get("html"))
    markdown = " ".join(m.value for m in at.markdown)
    check("critique never reaches HTML", "CRITIQUE_SENTINEL" not in html_blobs)
    check("zinger never reaches HTML", "ZINGER_SENTINEL" not in html_blobs)
    check("no raw tag from model text in HTML", "onerror=" not in html_blobs)
    check("critique is rendered as markdown text", "CRITIQUE_SENTINEL" in markdown)
    check("zinger is rendered as markdown text", "ZINGER_SENTINEL" in markdown)
    check("stylesheet is free of model text", "SENTINEL" not in stylesheet(at))

    print("\nRecused partner")
    at = render(
        "import ui\nfrom syndicate import PARTNERS, PartnerResult\n"
        "ui.inject_flair()\n"
        "ui.partner_card(PartnerResult(partner=PARTNERS[1], recused=True,"
        " error='Declined to review this pitch (policy).'))\n"
    )
    check("recused card renders", ran(at), why(at))
    check(
        "recused reason is shown",
        any("Declined" in c.value for c in at.caption),
    )

    print("\nLifecycle through one st.empty()")
    # The regression this file exists for.
    at = render(
        _FAKE_VERDICT
        + """
ui.inject_flair()
slots = [col.empty() for col in st.columns(len(PARTNERS))]
for slot, p in zip(slots, PARTNERS):
    with slot.container():
        ui.pending_card(p, status="waiting")
for slot, p in zip(slots, PARTNERS):
    with slot.container():
        ui.pending_card(p, status="running")
for slot, p in zip(slots, PARTNERS):
    with slot.container():
        ui.partner_card(PartnerResult(partner=p, verdict=verdict()))
st.write("LIFECYCLE_COMPLETE")
"""
    )
    exc = str(at.exception) if at.exception else ""
    check(
        "no StreamlitDuplicateElementKey",
        "DuplicateElementKey" not in exc,
        exc[:160],
    )
    check("lifecycle runs to completion", ran(at), why(at))
    check(
        "script reached the end",
        any("LIFECYCLE_COMPLETE" in m.value for m in at.markdown),
        why(at),
    )

    print("\nStandalone components")
    at = render(
        "import ui\nui.inject_flair()\nui.hero()\n"
        "ui.verdict_stamp(funded=False)\nui.verdict_stamp(funded=True)\n"
    )
    check("hero and stamps render", ran(at), why(at))
    blobs = " ".join(b.value for b in at.get("html"))
    check("hero emits the flame", "pr-flame" in blobs)
    check("hero emits the LED pill", "pr-led" in blobs)
    check("rejected stamp rendered", "Rejected by syndicate" in blobs)
    check("funded stamp rendered", "Funded by syndicate" in blobs)

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} check(s) failed: {', '.join(FAILURES)}\n")
        return 1
    print("✅ All UI checks passed (no API calls, no Phoenix, no key needed).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
