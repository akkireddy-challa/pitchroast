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
        
        Orchestrator -->|Parallel Async Fan-out| PartnerA[Sven Lindström<br/>Pragmatic Nordic B2B]
        Orchestrator -->|Parallel Async Fan-out| PartnerB[Balthazar Sterling<br/>High-Status Cynic]
        Orchestrator -->|Parallel Async Fan-out| PartnerC[Nova Spark<br/>Hyper-Growth Visionary]
        
        PartnerA --> PartnerAgg[Partner Roasts & Scores]
        PartnerB --> PartnerAgg
        PartnerC --> PartnerAgg
        
        PartnerAgg --> LeadPartner[Lead Partner Synthesis<br/>Consensus, Delusion Index & Term Sheet]
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

When a founder submits a pitch (text or pitch deck PDF), the `SyndicateEngine` triggers a parallel multi-agent evaluation:

```mermaid
sequenceDiagram
    autonumber
    actor Founder as Founder
    participant Engine as SyndicateEngine (Orchestrator)
    participant Sven as Sven Lindström (B2B Partner)
    participant Balthazar as Balthazar (Cynical Partner)
    participant Nova as Nova Spark (Moonshot Partner)
    participant Lead as Lead Partner Synthesizer
    participant Phoenix as Arize Phoenix Tracing

    Founder->>Engine: Submit Pitch ($4M ARR, AI Catapult)
    Engine->>Phoenix: Start Root Span ("syndicate_evaluation")
    
    par Async Fan-Out (Parallel LLM Calls)
        Engine->>Sven: Evaluate Unit Economics & Retention
        Engine->>Balthazar: Evaluate Moat & Defensibility
        Engine->>Nova: Evaluate TAM & Exit Velocity
    and Phoenix Instrumentation
        Sven-->>Phoenix: Record Tokens, Latency, Sentiment
        Balthazar-->>Phoenix: Record Tokens, Latency, Sentiment
        Nova-->>Phoenix: Record Tokens, Latency, Sentiment
    end

    Sven-->>Engine: Partner Evaluation 1
    Balthazar-->>Engine: Partner Evaluation 2
    Nova-->>Engine: Partner Evaluation 3

    Engine->>Lead: Synthesize Evaluations + Draft Term Sheet
    Lead-->>Phoenix: Record Synthesis Span + Cost Calculation
    Lead-->>Engine: Structured Verdict (Score, Delusion Index, Term Sheet)
    Engine->>Founder: Streamlit Generative UI (Badges, Roasts, Audio, PDF)
```

### Partner Personas & Temperature Matrix

| Partner | Role | Focus Area | Claude Temp | Tone |
| :--- | :--- | :--- | :---: | :--- |
| **Sven Lindström** | Nordic Managing Partner | EBITDA, NRR, churn, sustainable CAC | `0.4` | Dry, quantitative, pragmatist |
| **Balthazar Sterling** | Sand Hill Road Cynic | Moats, Big Tech copycats, margin erosion | `0.7` | Sarcastic, high-status, devastating |
| **Nova Spark** | Moonshot Accelerator GP | TAM, 100x velocity, frontier AI flywheel | `0.9` | High-energy, visionary, hype-detector |
| **Lead Partner** | Syndicate Chair | Consensus, valuation discount, term sheet | `0.5` | Decisive, institutional, formal |

---

## 🔭 Tracing & Observability Pipeline

PitchRoast integrates with **Arize Phoenix** (OpenTelemetry OSS Hub):

1. **Root Span**: Wraps the entire pitch evaluation transaction.
2. **Child Spans**:
   - `partner_evaluation_sven`: prompt tokens, completion tokens, latency, cost.
   - `partner_evaluation_balthazar`: prompt tokens, completion tokens, latency, cost.
   - `partner_evaluation_nova`: prompt tokens, completion tokens, latency, cost.
   - `lead_synthesis`: prompt tokens, completion tokens, latency, cost.
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
