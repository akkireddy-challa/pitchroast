# 🏛️ PitchRoast System Architecture

PitchRoast is an enterprise-grade, multi-agent AI investment committee simulator built for founders, hackathons, and VC scouts. It models the brutal, nuanced, and comedic dynamics of a Silicon Valley / Nordic venture capital partner meeting using **Anthropic Claude**, **Arize Phoenix**, and modern web rendering.

---

## 📐 High-Level Architecture

```mermaid
flowchart TD
    User([Founder / Judge / User]) -->|Input Pitch or Select Preset| Router{Mode Router}
    
    subgraph UI_Layer ["🖥️ Presentation & UI Layer"]
        Router -->|Default| Hotseat[Founder Hotseat UI]
        Router -->|?mode=admin| Observatory[Syndicate Observatory UI]
        Deck[3D Interactive Deck] -.->|reveal.js + Three.js| User
        Audio[ElevenLabs Voice Engine] -.->|Voice Pitching| User
        PDF[ReportLab Term Sheet PDF] -.->|Downloadable Artifact| User
    end

    subgraph Agent_Orchestration ["🤖 Multi-Agent Syndicate Committee"]
        Hotseat & Observatory --> Orchestrator[Syndicate Engine]
        
        Orchestrator -->|Parallel Async Fan-out| PartnerA[Max Market<br/>Market Sceptic]
        Orchestrator -->|Parallel Async Fan-out| PartnerB[Penny Pinch<br/>Financial Czar]
        Orchestrator -->|Parallel Async Fan-out| PartnerC[Tech Toby<br/>Systems CTO]
        
        PartnerA --> PartnerAgg[Partner Roasts & Scores]
        PartnerB --> PartnerAgg
        PartnerC --> PartnerAgg
        
        PartnerAgg --> LeadPartner[Boss Shark Synthesis<br/>Consensus, Delusion Index & Term Sheet]
    end

    subgraph Observability_Layer ["🔭 Observability & Telemetry (Phoenix)"]
        Orchestrator -.->|OpenTelemetry Spans| Phoenix[Arize Phoenix Hub]
        PartnerA -.->|Latency, Cost, Tokens| Phoenix
        PartnerB -.->|Latency, Cost, Tokens| Phoenix
        PartnerC -.->|Latency, Cost, Tokens| Phoenix
        LeadPartner -.->|Evaluation & Grounding| Phoenix
    end

    subgraph Defense_Layer ["🛡️ Zero-Crash Defense Engine"]
        Fallback[Local Mock Fallback Engine]
        PartnerA -.->|On Rate Limit / Timeout| Fallback
        PartnerB -.->|On Rate Limit / Timeout| Fallback
        PartnerC -.->|On Rate Limit / Timeout| Fallback
        LeadPartner -.->|On Error| Fallback
    end
```

---

## 🧠 Multi-Agent Parallel Fan-Out

When a founder submits a pitch (text or pitch deck preset), the `SyndicateEngine` triggers a parallel multi-agent evaluation:

```mermaid
sequenceDiagram
    autonumber
    actor Founder as Founder
    participant Engine as SyndicateEngine (Orchestrator)
    participant Max as Max Market (Market Sceptic)
    participant Penny as Penny Pinch (Financial Czar)
    participant Toby as Tech Toby (Systems CTO)
    participant Shark as Boss Shark (Managing Partner)
    participant Phoenix as Arize Phoenix Tracing

    Founder->>Engine: Submit Pitch (TAM, ARR, Product)
    Engine->>Phoenix: Start Root Span ("syndicate_evaluation")
    
    par Async Fan-Out (Parallel Claude Calls)
        Engine->>Max: Evaluate TAM & Customer Demand
        Engine->>Penny: Evaluate CAC/LTV & Cash Burn
        Engine->>Toby: Evaluate Architecture & Tech Debt
    and Phoenix Instrumentation
        Max-->>Phoenix: Record Tokens, Latency, Evaluation
        Penny-->>Phoenix: Record Tokens, Latency, Evaluation
        Toby-->>Phoenix: Record Tokens, Latency, Evaluation
    end

    Max-->>Engine: Partner Evaluation (Roast + Moat Critique)
    Penny-->>Engine: Partner Evaluation (Burn + Runway Critique)
    Toby-->>Engine: Partner Evaluation (Wrapper + Fragility Critique)

    Engine->>Shark: Synthesize Evaluations + Draft Term Sheet
    Shark-->>Phoenix: Record Synthesis Span + Cost Calculation
    Shark-->>Engine: Structured Verdict (Scores, Delusion Index, Term Sheet)
    Engine->>Founder: Streamlit Generative UI (Badges, Roasts, Audio, PDF)
```

### Partner Personas & Focus Matrix

| Partner | Role | Focus Domain | Architectural Focus |
| :--- | :--- | :--- | :--- |
| **Max Market** | The Market Sceptic | TAM, customer demand, buzzwords | Exposes fake demand, inflated TAM, and unvalidated claims |
| **Penny Pinch** | The Financial Czar | Unit economics, CAC/LTV, cash burn | Deconstructs negative margins, runaway burn, and pricing traps |
| **Tech Toby** | The Systems CTO | Architecture, wrappers, technical debt | Evaluates API fragility, duct-tape code, and AI wrapper risk |
| **Boss Shark** | Managing Partner | Consensus, valuation, term sheet | Synthesizes committee debate, issues covenants & 1% Pivot |

---

## 🔭 Tracing & Observability Pipeline

PitchRoast integrates with **Arize Phoenix** (OpenTelemetry OSS Hub):

1. **Root Span**: Wraps the entire pitch evaluation transaction (`syndicate_evaluation`).
2. **Child Spans**:
   - `partner_evaluation_marc`: prompt tokens, completion tokens, latency, cost.
   - `partner_evaluation_karen`: prompt tokens, completion tokens, latency, cost.
   - `partner_evaluation_torvalds`: prompt tokens, completion tokens, latency, cost.
   - `lead_synthesis_gekko`: prompt tokens, completion tokens, latency, cost.
3. **Evals**:
   - **Toxicity / Snark Metric**: Measures partner bite vs. constructive advice.
   - **Delusion Calibration**: Cross-references founder valuation claim against market benchmarks.
   - **Cost Accounting**: Exact cost per evaluation logged according to Claude Opus 5.5 / Sonnet 3.5 token pricing.

---

## 🛡️ Zero-Crash Resilience Architecture

In high-stakes hackathon settings, public Wi-Fi packet loss and Anthropic 429 rate limits are mitigated by a multi-tier fallback:

```mermaid
flowchart TD
    Call[Call Anthropic Claude API] --> Success{200 OK?}
    Success -->|Yes| Parse[Parse Structured JSON / Tool Output]
    Success -->|Timeout / 429 / 5xx| Handler[Resilience Handler]
    
    Parse --> Valid{Valid Schema?}
    Valid -->|Yes| Return[Return Real Output]
    Valid -->|Malformed| Repair[JSON Schema Repair Engine]
    
    Repair --> RepairSuccess{Repaired?}
    RepairSuccess -->|Yes| Return
    RepairSuccess -->|No| Handler
    
    Handler --> Mock[Local Persona Fallback Generator]
    Mock --> Stamp[Attach 'Demo Fallback Mode' Telemetry]
    Stamp --> Return
```

---

## 🎛️ Dual-Mode UI Architecture

PitchRoast provides two distinct operating modes cleanly separated by state and URL routing:

1. **Founder Hotseat (`/`)**:
   - Clean, immersive experience.
   - Large interactive roast cards, soundboard, 3D card tilt.
   - 1-click Downloadable Term Sheet (PDF).
   - Zero internal operator jargon.

2. **Syndicate Observatory (`/?mode=admin&key=pitchroast2026`)**:
   - Real-time LLM telemetry and token counters.
   - Phoenix OpenTelemetry span visualizer.
   - Multi-agent temperature and bias sliders.
   - Model switching (`Claude 3.5 Sonnet`, `Claude 3.5 Haiku`, `Claude 3 Opus`).
