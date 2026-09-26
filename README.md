# PitchRoast 🔥 — The Autonomous Venture Syndicate

[![Creator](https://img.shields.io/badge/Creator-Akkireddy%20Challa-FF8C00.svg)](https://github.com/akkireddy-challa)
[![Anthropic Claude](https://img.shields.io/badge/Powered%20by-Anthropic%20Claude-8A2BE2.svg)](https://console.anthropic.com)
[![Observability](https://img.shields.io/badge/Observability-Arize%20Phoenix%20OSS-orange.svg)](https://github.com/Arize-ai/phoenix)
[![Event](https://img.shields.io/badge/Claude%20Community-Stockholm%20Build%20Day-FF4500.svg)](https://luma.com/claudecommunity)
[![Track](https://img.shields.io/badge/Challenge-Track%201%3A%20Delight-success.svg)](#)
[![Presentation Deck](https://img.shields.io/badge/Live%20Presentation-GitHub%20Pages-blue.svg)](https://akkireddy-challa.github.io/pitchroast/)
[![Live App](https://img.shields.io/badge/Live%20App-Streamlit%20Cloud-red.svg)](https://akkireddy-challa-pitchroast-app-cwyolp.streamlit.app/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](#)

> **Created by Akkireddy Challa** for the **Stockholm | Fable 5.1 x Opus 5.5 Build Day** (Track 1: Delight). Presented by **Claude Community Stockholm**.  
> *"An autonomous venture committee of 4 ruthless AI partners who debate, dismantle, and deliver the brutal truth no VC says to your face—complete with live agent banter and a satirical term sheet."*

---

## ⚡ The Concept

Every founder has pitched an investor and received the standard diplomatic reply: *"Great deck, let's keep in touch!"* 

In Silicon Valley and Nordic startup hubs, that's code for: *"Your unit economics are broken and a college student could build your product this weekend."*

**PitchRoast eliminates polite lies.** It convenes a four-partner investment committee that analyzes your startup pitch in parallel, computes quantitative risk metrics, debates your business model in real time, and drafts an absurd satirical term sheet.

---

## 🏛️ Autonomous Agent Syndicate

PitchRoast orchestrates four distinct Claude-powered agents into a cohesive investment committee:

```mermaid
graph TD
    A[Founder Pitch Submission] --> B[PitchRoast Multi-Agent Committee]
    
    subgraph Boardroom Debate
        B --> C["🕶️ <b>Max Market</b><br>The Idea Judge<br><i>Tears down fake demand & big dreams</i>"]
        B --> D["💰 <b>Penny Pinch</b><br>The Money Boss<br><i>Attacks piggy bank burn & bad unit math</i>"]
        B --> E["💻 <b>Tech Toby</b><br>The Tech Builder<br><i>Exposes duct-tape code & fake AI</i>"]
    end

    C --> F[Syndicate Consensus Engine]
    D --> F
    E --> F

    F --> G["🦈 <b>Boss Shark</b><br>The Big Boss<br><i>Drafts Funny Term Sheet & Final Score</i>"]
    
    G --> H["📊 Quantitative Scorecard<br>• Make-Believe Index (%)<br>• Real Tech Score (0-10)<br>• Runway (Months)<br>• Pre-Money Valuation"]
    G --> I["📜 Satirical Term Sheet<br><i>With Absurd Mandatory Covenants</i>"]
    G --> J["💡 The 1% Pivot<br><i>Actionable path to real revenue</i>"]
```

### The Committee Judges

| Agent | Persona & Title | Focus Area |
| :--- | :--- | :--- |
| **🕶️ Max Market** | The Idea Judge | Calls out make-believe customer numbers, buzzwords, and ideas nobody actually asked for. |
| **💰 Penny Pinch** | The Money Boss | Destroys ideas that spend $100 to make $1, charging pennies for things that cost dollars to run. |
| **💻 Tech Toby** | The Tech Builder | Exposes gadgets held together with duct tape and simple websites pretending to be super-smart AI. |
| **🦈 Boss Shark** | The Big Boss | Combines all votes, makes the final call (Deal or No Deal), and issues funny contract rules. |

---

## 📊 Live Scoring Engine

PitchRoast computes four quantitative indicators for every submission:
* **Delusion Index (%)**: How far the founder's assumptions diverge from reality.
* **True Moat Score (0–10)**: Resistance to being cloned by an intern in 48 hours.
* **Survival Runway (Months)**: Estimated time before emergency bridge loan or insolvency.
* **Pre-Money Valuation**: A realistic market assessment (e.g. *"$14.50 and a lukewarm kanelbulle"*).

---

## 🌐 Live Deployments

| Component | Description | URL |
| :--- | :--- | :--- |
| 🎯 **Founder Hot Seat (Live App)** | Public interactive boardroom for live audience pitches | **[akkireddy-challa-pitchroast-app-cwyolp.streamlit.app](https://akkireddy-challa-pitchroast-app-cwyolp.streamlit.app/)** |
| 📽️ **Interactive Pitch Deck** | Autonomous AI voice narrated presentation (GitHub Pages) | **[akkireddy-challa.github.io/pitchroast](https://akkireddy-challa.github.io/pitchroast/)** |
| 🔬 **Syndicate Observatory** | Internal operator command centre (Passkey: `pitchroast2026`) | **[Observatory Direct Access](https://akkireddy-challa-pitchroast-app-cwyolp.streamlit.app/?mode=admin&key=pitchroast2026)** |

---

## 🛡️ Zero-Crash Demo Resilience Mode

Hackathon Wi-Fi drops and expired API keys frequently crash live demos on stage. **PitchRoast is engineered for 100% demo uptime**:
- **Automatic Fallback**: If an Anthropic API key is expired, unconfigured, or hits rate limits, the engine gracefully activates the **Zero-Crash Simulation Engine**.
- **Realistic Deliberations**: All 4 partners debate with bespoke, razor-sharp satirical critiques tailored to Swedish tech culture (`☕ FikaSync`, `💳 Klarna for Regret`, `🤖 AI Standup Bot`, `☕ Oat Milk Web3`) and arbitrary audience pitches.
- **Zero Interruption**: Live audience testing and stage demonstrations never fail or show raw error screens.
- **Instant Live Claude Upgrade**: When a valid Claude API key is supplied (in Streamlit Secrets, environment, or the Observatory), live `claude-opus-5-5` and `claude-fable-5-1` take over immediately.

---

## 🚀 Quickstart

### 1. Clone & Enter Directory
```zsh
git clone https://github.com/akkireddy-challa/pitchroast.git
cd pitchroast
```

### 2. Activate Virtual Environment
```zsh
source .venv/bin/activate
# Or create fresh with uv:
uv sync
```

### 3. Configure Your Anthropic Key (Optional)
```zsh
./set_key.sh sk-ant-your-key-here
```
*(If omitted, PitchRoast boots directly in Zero-Crash Resilience Mode with full interactive roasts!)*

### 4. Launch the Interactive Boardroom
```zsh
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser. `app.py` is the only runnable
entrypoint; every other module is imported by it.

### Two doors into the same session

| URL | View | Audience |
| --- | --- | --- |
| `http://localhost:8501/` or `?mode=founder` | 🎯 **Founder Hot Seat** | Founders. Quick pitches, presets (FikaSync, Klarna for Regret), a VC-mood dial, the committee roster, the scorecard and the stamped term sheet. Frictionless and public. |
| `http://localhost:8501/?mode=admin` | 🔬 **Syndicate Observatory** | Judges and operators. PIN-protected (`pitchroast2026`). Phoenix trace hub, token/credit telemetry against the €100 voucher, model + effort orchestration, panel concurrency, and deliberation traces. |

The switch sits at the top right of either view and rewrites the URL, so both
links are shareable. **The two views share one session**: run a pitch in the Hot
Seat, flip to the Observatory, and the same verdict is there with its traces and
token economics — flipping never costs an API call.

The split is a UX boundary, not an authorisation one. Anyone can type
`?mode=admin`; the Observatory only ever shows local, non-secret operational
data, and the API key field is write-only.

**Seating the panel.** The Observatory's *Partner seats* control decides who
reviews the pitch: drop a partner to skip that line of attack and its API call.
One seat means two calls per roast instead of four. The managing partner is not
optional — it synthesises whoever sat and issues the term sheet.

**Credit telemetry.** The voucher tracker counts only roasts run in this app, at
list price, with no cache discount. `claude-opus-5-5` has no published
per-token rate, so it is charged at the Opus tier and labelled as an assumption;
set `PITCHROAST_PRICING` once you have confirmed the real number in the Console.

### Module map

| File | Role |
| --- | --- |
| `app.py` | Router, page shell, mode switch |
| `founder.py` / `admin.py` | The two views |
| `board.py` | Verdict rendering + the live run, shared by both |
| `state.py` | Session state, operator settings, Phoenix bootstrap |
| `costs.py` | Token → credit arithmetic |
| `syndicate.py` / `observability.py` / `ui.py` | Engine, tracing, components |

---

## 🎤 Stage Presentation Options

### Option A: 🤖 Autonomous AI Clone Mode (Zero Stage Fright!)
You don't need to speak or worry about public speaking! The presentation deck features an autonomous audio voiceover powered by the AI Clone of Akkireddy:

1. **Akkireddy's 5-Second Intro at the Mic**:
   > *"Good evening Claude Community Stockholm! In the spirit of autonomous AI agents, why have a tired human pitch on stage when you can have an AI clone do it? Please welcome: my digital AI clone."*
2. **Press `P` on the keyboard (or click `🎙️ Let AI Pitch`)**:
   - The AI Clone introduces itself:
     > *"Hello Claude Community Stockholm! I am the AI clone of human Akkireddy Challa. My human original built this entire project tonight for the Claude Community Fable 5.1 x Opus 5.5 Build Day. But why have a tired human pitch on stage when you can have a superior AI clone do it with zero stage fright? Welcome to PitchRoast! Let's see why your business idea is probably terrible."*
   - The AI narrates all 8 slides with live sound waves and real-time subtitles, automatically advancing smoothly from slide to slide!

---

### Option B: 🎙️ Live Human Pitch (2-Minute Script)
If you want to speak yourself, use this simple, kid-friendly script:

1. **The Hook (0:00 - 0:25)**:
   > *"Have you ever told a friend about a cool idea, and they said: 'Oh wow, that’s so great! You should totally do that!' ... But deep down, you knew it was actually a terrible idea, and they were just being nice?  
   > Founders waste months of time and burn all their savings because people are too polite to tell them the truth. We built PitchRoast to tell you the funny, honest truth in 15 seconds!"*

2. **Meet The Judges (0:25 - 0:45)**:
   > *"We have four AI judges testing your pitch:  
   > • Max Market asks: 'Will anyone actually wake up and pay money for this?'  
   > • Penny Pinch counts your pennies: 'You're spending your whole allowance to make zero dollars!'  
   > • Tech Toby looks under the hood: 'You didn't build smart AI, you just taped an iPad to a broom!'  
   > • And Boss Shark gives the final verdict: Deal or No Deal!"*

3. **The Live Demo (0:45 - 1:25)**:
   > *(Click on 'Klarna for Regret' or 'FikaSync Bun Police' and press Convene Committee)*  
   > *"Look at that! In 14 seconds, all three judges talk at the exact same time.  
   > Boss Shark says: '96% Make-Believe! Valuation: 25 Kronor and a half-eaten cinnamon bun!'"*

4. **The Big Finish (1:25 - 1:45)**:
   > *"Behind the scenes, we use Anthropic Claude and live local telemetry, tracking our 100 Euro hackathon voucher in real-time.  
   > PitchRoast: The honest VC that tells you the truth in 15 seconds, and costs $0 instead of giving away your company. Thank you!"*

---

## 🛠️ Tech Stack
* **Language & Runtime**: Python 3.12+ / 3.14 (Mise, uv)
* **Frontend**: Streamlit 1.64 (Custom Dark Glassmorphism CSS)
* **AI Orchestration**: Anthropic Python SDK (`claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`)
* **Observability & Tracing**: Arize Phoenix OSS (OpenInference / OpenTelemetry native spans, token metrics, and latency tracking)
* **Linter & Standards**: Ruff 0.16
