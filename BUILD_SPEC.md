# PitchRoast 🔥 — Build Specification

> **Version**: 1.0 · **Status**: Draft · **Owner**: aue729
> **Companion to** [`SPEC.md`](./SPEC.md) — that document defines *what PitchRoast is* (architecture
> narrative, UI/UX, stage playbook). This one defines *what has to be true for it to build, run, and
> survive the 20:30 demo*: contracts, model parameters, defects, and acceptance criteria.

---

## 1. Scope

**In scope (v1)** — Streamlit UI (`app.py`), headless CLI runner (`run_demo.py`), Anthropic Messages
API as the only backend, local Arize Phoenix OSS tracing, `.txt` term sheet export.

**Out of scope (v1)** — persistence, accounts, rate limiting, deployment beyond localhost, any
non-Anthropic provider.

---

## 2. Current State vs. Target State

`SPEC.md` §1 describes a four-agent committee with a synthesis layer. **The shipped code is a single
Claude call** that emits all four voices inside one JSON object (`app.py:231`, `run_demo.py:92`).
That is a defensible v1 — fast, cheap, demos well — but the spec must not pretend otherwise.

| Capability | Current (`main`) | Target (§6) |
| :--- | :--- | :--- |
| Agent execution | 1 call, 1 system prompt, 4 personas in one JSON | 3 parallel partner calls + 1 shark synthesis call |
| Debate | Simulated — model writes all four voices at once | Real — shark receives the partners' actual output |
| Output contract | Prose instruction + `re.search(r'\{.*\}')` salvage | `output_config.format` JSON schema, no regex |
| Streaming | None (blocking `messages.create`) | Per-partner card fills as each call returns |
| Thinking drawer | Renders, but always empty (§9 defect 1) | Populated via `display: "summarized"` |
| XSS surface | Model text injected with `unsafe_allow_html=True` | Escaped (§8.3) |

Everything marked *(v1.1)* below is **not yet built**.

---

## 3. Components

| Component | File | Responsibility |
| :--- | :--- | :--- |
| Streamlit UI | `app.py` | Input form, model/brutality controls, card rendering, export |
| CLI runner | `run_demo.py` | Headless end-to-end run — stage fallback and smoke test |
| Connectivity probe | `test_connection.py` | Verifies key + model reachability, prints token usage |
| Task automation | `Makefile` | `app`, `demo`, `test`, `phoenix`, `check`, `status`, `push` |
| Key bootstrap | `set_key.sh` | Writes `.env`, then runs the probe |
| Isolated Claude Code | `claude_hackathon.sh` | Pins `ANTHROPIC_BASE_URL` to the public API, bypasses Telia LiteLLM |

*(v1.1)* Extract the shared prompt + schema into `syndicate.py`. The 30-line system prompt is
currently duplicated byte-for-byte across `app.py:195-224` and `run_demo.py:59-88`, so every prompt
tweak has to be made twice or the CLI fallback silently diverges from the UI.

---

## 4. Model Configuration

Verified against `GET /v1/models` with the event key on 2026-09-25. All three carry **1M input tokens,
128K max output, structured outputs, and adaptive-only thinking**.

| UI label | Model ID | Released | Role |
| :--- | :--- | :--- | :--- |
| ⚡ Fable 5.1 — fast iteration | `claude-fable-5-1` | 2026-08-28 | Prompt tuning, CLI demo, credit conservation |
| 🧠 Opus 5.5 — stage demo | `claude-opus-5-5` | 2026-09-21 | **Live demo.** Newest; deepest satirical reasoning |
| 🏛️ Opus 5 — classic frontier | `claude-opus-5` | 2026-07-24 | Stable fallback if 5.5 misbehaves under load |

Per-token pricing for Opus 5.5 is not in any cached table available here — **confirm it in the Console
before the demo** so the 100€ credit budget is real and not assumed. Fable 5.1 is the most expensive
per token of the three despite being the "dev" model; it is the fast choice, not the cheap one.

### 4.1 Request parameters

```python
client.messages.create(
    model=selected_model,
    max_tokens=8000,                                        # 2048 today — see §9 defect 2
    system=[{"type": "text", "text": SYSTEM,
             "cache_control": {"type": "ephemeral"}}],
    thinking={"type": "adaptive", "display": "summarized"},  # §9 defect 1
    output_config={"effort": "medium", "format": SCHEMA},    # §5
    messages=[{"role": "user", "content": pitch}],
)
```

### 4.2 Hard constraints — each returns HTTP 400

- **No `temperature` / `top_p` / `top_k`.** Sampling parameters are removed on this model generation.
  The "Brutality Index" slider must stay exactly what it already is — a float interpolated into the
  *system prompt text* (`app.py:229`), never an API parameter. Its UI label should drop
  "(Temperature)", which currently promises something the code cannot do.
- **No `budget_tokens`.** The Models API reports `thinking.types.enabled.supported: false` on all
  three models — only `adaptive` is accepted. Control depth with `output_config.effort`.
- **No assistant prefill.**

### 4.3 Effort & cost

`effort: "medium"` is right for this workload: short-form creative writing, not long-horizon agentic
work, so `high`/`xhigh` buys little and costs real credits. Budget roughly 600 input / 900 output
tokens per single-call run. The v1.1 four-call design is ~4× that — mark the shared persona preamble
with `cache_control: {"type": "ephemeral"}` so the three partner calls read the prefix from cache
instead of paying for it three times.

### 4.4 Refusal handling

PitchRoast is an insult generator pointed at user-supplied text. A hostile or slur-laden pitch can
legitimately return `stop_reason: "refusal"` — HTTP 200, `stop_details.category` populated, no usable
content. Check `stop_reason` **before** reading `content`, and render an in-character decline ("the
committee has declined to take this meeting") instead of a stack trace. This is a live risk with an
audience typing their own pitches into the laptop after the demo.

---

## 5. Data Contract

The verdict is one JSON object. Enforce it with `output_config.format` — all three models support
structured outputs, so the current `re.search(r'\{.*\}', text, re.DOTALL)` salvage path
(`app.py:253`, `run_demo.py:101`) should be deleted. It is greedy, mis-parses any prose containing
braces, and raises an unhandled `JSONDecodeError` in the CLI.

```python
SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "delusion_index", "moat_score", "runway_months", "pre_money_val",
            "marc_critique", "karen_critique", "torvalds_critique",
            "satirical_term_sheet", "the_pivot",
        ],
        "properties": {
            "delusion_index":    {"type": "integer", "minimum": 0, "maximum": 100},
            "moat_score":        {"type": "integer", "minimum": 0, "maximum": 10},
            "runway_months":     {"type": "integer", "minimum": 1, "maximum": 12},
            "pre_money_val":     {"type": "string"},
            "marc_critique":     {"type": "string"},
            "karen_critique":    {"type": "string"},
            "torvalds_critique": {"type": "string"},
            "satirical_term_sheet": {
                "type": "object",
                "additionalProperties": False,
                "required": ["valuation", "investment_amount",
                             "liquidation_pref", "covenants"],
                "properties": {
                    "valuation":         {"type": "string"},
                    "investment_amount": {"type": "string"},
                    "liquidation_pref":  {"type": "string"},
                    "covenants": {"type": "array", "minItems": 3, "maxItems": 5,
                                  "items": {"type": "string"}},
                },
            },
            "the_pivot": {"type": "string"},
        },
    },
}
```

In `syndicate.py`, prefer the Pydantic path — `client.messages.parse(..., output_format=Verdict)`
returns a validated `response.parsed_output` and removes hand-written `json.loads` entirely.

### 5.1 Field semantics

| Field | Meaning | Rendering |
| :--- | :--- | :--- |
| `delusion_index` | Gap between the founder's claims and reality | `st.metric`, `%`, inverse delta |
| `moat_score` | Resistance to a weekend clone | `st.metric`, `x / 10`, inverse delta |
| `runway_months` | Months before an emergency bridge | `st.metric`, months, inverse delta |
| `pre_money_val` | Satirical valuation string | `st.metric`, raw string |
| `*_critique` | 2–3 sentences per partner | Agent card, **escaped** |
| `satirical_term_sheet` | Fake deal terms | Stamped monospace block + `.txt` export |
| `the_pivot` | One genuinely actionable idea — the payload that earns the joke | Term sheet footer |

The renderer's fallback defaults (`app.py:263-269`) invent plausible numbers — `94`, `1.5`, `2` — when
a key is missing. Schema enforcement makes them unreachable; keep them as a last-resort guard only.
Never present a fabricated number to the audience as a model output, least of all the `94%` that also
appears in the stage script.

---

## 6. Agent Specification *(v1.1)*

Four agents, four API calls, four Phoenix spans.

| # | Agent | Role | Attacks |
| :-- | :--- | :--- | :--- |
| 1 | 🕶️ **Marc Low-res** | General Partner | TAM inflation, "no competitors", buzzword soup, fake moats |
| 2 | 📊 **Karen Burn-rate** | Quant CFO | Negative gross margin, CAC > LTV, cloud bill, 47-day runway |
| 3 | 💻 **Torvalds-9000** | Systems CTO | "An API call wrapped in Tailwind", tech debt, latency, hallucination risk |
| 4 | 🦈 **Gordon Gekko AI** | Managing Partner | Synthesis only — valuation haircut, 5× participating preferred, covenants |

**Orchestration**: agents 1–3 run concurrently (`asyncio.gather` over `AsyncAnthropic`, or a
`ThreadPoolExecutor` around the sync client). Agent 4 blocks on all three and receives their verbatim
critiques in its user message — that is the difference between a debate and three monologues.
Agents 1–3 return `{critique, scores}`; agent 4 returns the term sheet, the reconciled scorecard, and
the pivot.

**Partial failure**: if one partner call fails, render the other two, mark the third card "recused",
and let the shark synthesise from what it has. A single 429 must not kill the demo.

**Guardrail**: the satire targets the *pitch*, never a real named person or company. State this
explicitly in every system prompt.

---

## 7. UI Behaviour

### 7.1 States

| State | Trigger | Behaviour |
| :--- | :--- | :--- |
| Idle | Load | Form only |
| Invalid | No key | `st.error` — "provide an Anthropic API Key" |
| Invalid | Empty pitch | `st.warning` |
| Running | Click | `st.spinner("Convening the 4 partners via {model}…")` |
| Success | Valid verdict | Scorecard → three cards → stamped term sheet → export + telemetry |
| Refused | `stop_reason == "refusal"` | In-character decline card (§4.4) |
| Error | `APIError` / parse failure | `st.error` + "check key and credits" |

### 7.2 Result persistence

Results live in local variables, so **any sidebar interaction after a run clears the output**.
Nudging the brutality slider or the model selector mid-presentation wipes the scorecard off the
screen. *(v1.1)* Store the verdict in `st.session_state` and render from there.

Visual design — glassmorphism values, animation names, stamp treatment — is specified in `SPEC.md` §2
and not duplicated here.

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Path | Target |
| :--- | :--- |
| Single-call verdict (Fable 5.1) | < 15 s p95 |
| Single-call verdict (Opus 5.5, effort medium) | < 25 s p95 |
| Four-call verdict *(v1.1)*, partners parallel | < 35 s p95 |
| Streamlit first paint | < 2 s |

The demo slot allows ~60 s for the live run. If any path approaches the SDK's 10-minute default
timeout, switch to `client.messages.stream()` with `.get_final_message()`.

### 8.2 Observability

Arize Phoenix OSS launched in-process (`px.launch_app(run_in_thread=True)`) with
`AnthropicInstrumentor()`, UI on `http://localhost:6006`. Zero external cost; no data leaves the
machine. `setup_observability()` is wrapped in `@st.cache_resource` so Streamlit reruns don't spawn a
second Phoenix instance — keep it that way.

Required span attributes: model ID, input/output tokens, latency, `stop_reason`, and *(v1.1)* agent
name. The bare `except Exception: return None` (`app.py:114`) hides misconfiguration completely; log
at WARNING before returning, or the sidebar will read "tracing offline" with no way to find out why.

### 8.3 Security

| Requirement | Status |
| :--- | :--- |
| Key never committed | ✅ `.env` gitignored, `.env.example` holds a placeholder |
| Key masked in UI | ✅ `type="password"` |
| Traffic pinned to `api.anthropic.com` | ✅ explicit `base_url`; Telia LiteLLM bypassed by design |
| Key never logged in full | ⚠️ `run_demo.py:26` prints first 14 **and last 6** characters. Print the prefix only — this runs on a projector. |
| **Model output not rendered as raw HTML** | ❌ **Must fix.** `app.py:283/295/307` concatenate `data['*_critique']` into `st.markdown(..., unsafe_allow_html=True)`. A pitch that induces the model to emit a `<script>` or an unclosed tag injects into the page — and the audience will be typing the pitches. Run every model string through `html.escape()`. |
| No PII / customer data | ✅ user-supplied pitch text only |

Per Telia policy this is a personal, non-production hackathon project on a personal event key. Company
code and data must not be pasted into it.

### 8.4 Reliability

Catch the typed chain — `AuthenticationError` → `NotFoundError` → `RateLimitError` → `APIStatusError`
→ `APIConnectionError` — rather than the single bare `except Exception` at `app.py:350`, which
currently renders "check your credits" for what may be a JSON parse bug. The SDK auto-retries
408/409/429/5xx twice; leave `max_retries` at its default. The CLI must exit non-zero on failure so
`make demo` is usable as a smoke test.

---

## 9. Known Defects

Ordered by demo risk.

| # | Severity | Location | Defect | Fix |
| :-- | :--- | :--- | :--- | :--- |
| 1 | **High** | `app.py:238-250` | The 🧠 *VC Partner Deliberation* drawer never appears. `thinking.display` defaults to `"omitted"` on all three models, so `block.thinking` is an empty string and the expander is skipped. `SPEC.md` §3 sells this as an Opus 5.5 feature. | Send `thinking={"type": "adaptive", "display": "summarized"}` |
| 2 | **High** | `app.py:234` | `max_tokens=2048` against a 128K-capable model. A long verdict truncates mid-JSON and the parse fails *after* the credits are spent. | Raise to 8000 |
| 3 | **High** | `app.py:283,295,307` | Model output rendered as unescaped HTML | `html.escape()` (§8.3) |
| 4 | Medium | `app.py:253`, `run_demo.py:101` | Greedy regex JSON salvage; `JSONDecodeError` unhandled in the CLI | `output_config.format` (§5) |
| 5 | Medium | `app.py` | No `session_state` — any sidebar change clears the results mid-demo | Cache the verdict (§7.2) |
| 6 | Medium | `app.py:135` | Slider labelled "(Temperature)" but never sent as `temperature` — and must not be, it 400s | Rename to "Brutality Index" |
| 7 | Low | `app.py:25` | `font-family: 'Plus+Jakarta Sans'` — the `+` belongs only in the Google Fonts URL, so the custom font never applies and the UI silently falls back to sans-serif | `'Plus Jakarta Sans'` |
| 8 | Low | `app.py:168` | `if selected_preset` is always truthy (the placeholder is a non-empty string key), so the guard is dead code | Compare against the placeholder key |
| 9 | Low | both entrypoints | 30-line system prompt duplicated verbatim | Extract `syndicate.py` |
| 10 | Low | `set_key.sh` | No `set -euo pipefail`; `.env` written world-readable | Add the guard, `chmod 600 .env` |

---

## 10. Build, Run, Verify

**Prerequisites**: Python 3.12+, `.venv` at the repo root, `ANTHROPIC_API_KEY`.

```zsh
./set_key.sh sk-ant-...   # writes .env, then probes connectivity
make test                 # connectivity + token usage
make demo                 # headless end-to-end run (Fable 5.1)
make app                  # Streamlit UI  → http://localhost:8501
make phoenix              # traces        → http://localhost:6006
make check                # ruff --fix --isolated
```

Dependencies are implicit in `.venv` and recorded nowhere. *(v1.1)* Add `pyproject.toml` pinning
`anthropic`, `streamlit`, `python-dotenv`, `arize-phoenix`,
`openinference-instrumentation-anthropic`, and `ruff`. As it stands, `make app` fails on any machine
that is not this one — including a borrowed laptop at the venue.

---

## 11. Acceptance Criteria

**v1 — ship for the demo**

- [ ] `make test` succeeds against all three models in §4.
- [ ] `make demo` prints a complete scorecard, three critiques, ≥3 covenants, and a pivot.
- [ ] All three UI presets produce a full verdict with no traceback.
- [ ] Defects 1, 2, and 3 are fixed.
- [ ] The thinking drawer actually renders content on Opus 5.5.
- [ ] Phoenix shows one span per API call with token counts.
- [ ] Term sheet export downloads and opens as readable text.
- [ ] `make check` is clean.
- [ ] End-to-end run completes inside the 60 s demo slot.

**v1.1 — real multi-agent**

- [ ] Four distinct API calls, one span per agent in Phoenix.
- [ ] Partners 1–3 execute concurrently; wall clock < sum of individual latencies.
- [ ] The shark's input contains the three partners' verbatim critiques.
- [ ] Responses are schema-validated; no regex JSON extraction remains.
- [ ] One failing partner degrades to "recused" instead of failing the run.
- [ ] Results survive sidebar interaction.

---

## 12. Stage Contingencies

The playbook itself is `SPEC.md` §5. These are the failure paths:

1. **Warm the cache** — run one verdict before going on stage so the first live call isn't the slow one.
2. **Second terminal open on `make demo`** — if Streamlit stalls, the CLI is the same demo without the CSS.
3. **Last successful CLI output saved to a file** — if the venue network is hostile, that transcript is the backup slide.
4. **Fall back 5.5 → 5 → Fable 5.1**, in that order, if a model is slow or rate-limited. All three are provisioned on the event key.

---

## 13. Open Questions

1. Should the shark ever *fund* a pitch? A rare "term sheet accepted" path would make the roast land
   harder by contrast — right now every possible outcome is rejection, and the `❌ REJECTED BY
   SYNDICATE` stamp is unconditional.
2. Are the four indices reconciled from the partners' individual scores, or issued solely by the
   shark? §6 assumes reconciliation; the current code has neither.
3. Is a shareable permalink worth the persistence layer it needs, or is the `.txt` export enough for
   the event?
