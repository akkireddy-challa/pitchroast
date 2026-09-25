import json
import os
import re

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="PitchRoast 🔥 | Autonomous VC Syndicate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# World-Class Dark Theme, Glassmorphism, and CSS Keyframe Animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus+Jakarta Sans', sans-serif;
    }

    /* Keyframe Animations */
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); }
        50% { box-shadow: 0 0 30px rgba(255, 69, 0, 0.5); }
        100% { box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); }
    }

    @keyframes flameFlicker {
        0%, 100% { transform: scale(1) rotate(0deg); }
        25% { transform: scale(1.05) rotate(-2deg); }
        75% { transform: scale(0.97) rotate(2deg); }
    }

    @keyframes ledBlink {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    .hero-container {
        text-align: center;
        padding: 2.2rem 1.5rem 1.8rem 1.5rem;
        background: radial-gradient(circle at 50% 0%, rgba(255, 69, 0, 0.18) 0%, rgba(15, 23, 42, 0.6) 75%);
        border-radius: 20px;
        margin-bottom: 1.8rem;
        border: 1px solid rgba(255, 69, 0, 0.3);
        animation: pulseGlow 4s infinite ease-in-out;
        position: relative;
        overflow: hidden;
    }

    .hero-icon {
        display: inline-block;
        font-size: 3rem;
        animation: flameFlicker 2.5s infinite ease-in-out;
        margin-bottom: 0.2rem;
    }

    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4500 0%, #FF8C00 50%, #FFD700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
        letter-spacing: -0.035em;
    }

    .hero-subtitle {
        color: #CBD5E1;
        font-size: 1.18rem;
        font-weight: 500;
        max-width: 760px;
        margin: 0 auto 0.8rem auto;
        line-height: 1.5;
    }

    .live-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34D399;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .led-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
        animation: ledBlink 1.8s infinite ease-in-out;
    }

    /* Agent Card Styling */
    .agent-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.4rem;
        height: 100%;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
        transition: transform 0.25s ease, border-color 0.25s ease;
        animation: slideUpFade 0.6s ease-out;
    }
    .agent-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 69, 0, 0.5);
    }

    .agent-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.8rem;
    }

    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .badge-gp { background: rgba(239, 68, 68, 0.2); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-cfo { background: rgba(59, 130, 246, 0.2); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-cto { background: rgba(16, 185, 129, 0.2); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.4); }
    
    .agent-name {
        font-size: 1.15rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-top: 0.2rem;
    }
    .agent-title {
        font-size: 0.8rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 0.9rem;
    }

    /* Term Sheet & Stamp */
    .term-sheet-wrapper {
        position: relative;
        background: #0B0F19;
        border: 2px solid #F59E0B;
        border-radius: 16px;
        padding: 1.8rem;
        margin-top: 1.5rem;
        font-family: 'JetBrains Mono', monospace;
        box-shadow: 0 10px 40px rgba(245, 158, 11, 0.15);
        overflow: hidden;
    }

    .stamp-badge {
        display: inline-block;
        border: 3px solid #EF4444;
        color: #EF4444;
        font-weight: 900;
        font-size: 1.3rem;
        text-transform: uppercase;
        padding: 0.4rem 1.2rem;
        border-radius: 8px;
        transform: rotate(-5deg);
        letter-spacing: 0.12em;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
        margin-bottom: 1.2rem;
    }

    .metric-gauge-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.1rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    .metric-value-huge {
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        margin: 0.2rem 0;
    }
    .metric-label-sub {
        font-size: 0.78rem;
        text-transform: uppercase;
        color: #94A3B8;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# Observability Init
@st.cache_resource
def setup_observability():
    """Initializes Arize Phoenix OSS tracing locally without consuming external API credits."""
    try:
        import phoenix as px
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        session = px.launch_app(run_in_thread=True)
        AnthropicInstrumentor().instrument()
        return session.url
    except Exception:  # noqa: BLE001
        return None

phoenix_url = setup_observability()

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-icon">🔥</div>
    <div class="hero-title">PitchRoast Syndicate</div>
    <div class="hero-subtitle">Four autonomous AI venture partners debate, dismantle, and deliver the brutal truth no VC says to your face.</div>
    <div class="live-status-pill">
        <div class="led-dot"></div>
        Autonomous Committee Ready • Stockholm Build Day
    </div>
</div>
""", unsafe_allow_html=True)

# Model configuration mapping
MODEL_MAP = {
    "⚡ Claude Fable 5.1 (Fast & Token-Efficient — Recommended for Testing)": "claude-fable-5-1",
    "🧠 Claude Opus 5.5 (Deep Extended Thinking — Best for Final Demo)": "claude-opus-5-5",
    "🏛️ Claude Opus 5 (Classic Frontier)": "claude-opus-5"
}

# Sidebar
with st.sidebar:
    st.header("⚙️ Syndicate Controls")
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Configured from event voucher key."
    )
    
    selected_model_label = st.selectbox(
        "Active Frontier Model",
        list(MODEL_MAP.keys()),
        index=0,
        help="Use Fable 5.1 during development to conserve credits; switch to Opus 5.5 for the live demo."
    )
    selected_model = MODEL_MAP[selected_model_label]

    roast_mode = st.select_slider(
        "🔥 Brutality Mode",
        options=["Mild Reality Check", "Standard Sand Hill Roast", "Scorched Earth Term Sheet"],
        value="Standard Sand Hill Roast"
    )

    st.markdown("---")
    st.markdown("### 🔭 Arize Phoenix Observability")
    if phoenix_url:
        st.success("✅ Tracing Active (Local OSS)")
        st.markdown(f"📊 [**Open Phoenix Tracing UI**]({phoenix_url})")
        st.caption("Tracks OTEL spans, latency, token spend, and agent prompts locally at 0 credit cost.")
    else:
        st.caption("Phoenix tracing offline.")

    st.markdown("---")
    st.markdown("### 🏛️ Committee Members")
    st.markdown("""
    • **🕶️ Marc Low-res** (General Partner)  
    • **📊 Karen Burn-rate** (Quant CFO)  
    • **💻 Torvalds-9000** (10x Grumpy CTO)  
    • **🦈 Gordon Gekko AI** (Syndicate Shark)
    """)
    st.markdown("---")
    st.caption("⚡ Built with Anthropic Claude for Stockholm Build Day at Epicenter.")

# Fast Startup Presets
preset_options = {
    "Select a pre-loaded startup idea or enter your own...": "",
    "☕ Autonomous Oat Milk Micro-Roastery with Web3 Proof-of-Foam": 
        "A decentralized network of countertop espresso machines that roast small-batch Nordic oat milk using on-chain temperature consensus. Users stake OAT tokens for latte art NFTs. Market size: $400B addressable beverage space.",
    "🤖 AI Meeting Proxy that says 'Blocked by Backend' in 14 accents": 
        "An autonomous AI agent avatar that joins daily Scrum standups on Zoom/Teams, randomly sighs, checks its phone, and responds 'I am blocked by the infrastructure backend' whenever your name is called. B2B SaaS priced at $49/engineer/month.",
    "🐾 Uber for Cats: Feline Scooter On-Demand": 
        "High-density urban cat affection. When an office worker feels burnt out, our app dispatches an autonomous electric scooter carrying a pre-vetted emotional support cat to their office lobby for a 15-minute petting session.",
    "🍕 Tinder for Leftover Pizza: Peer-to-Peer Slice Swapping":
        "A location-based peer-to-peer marketplace where college students swipe right on half-eaten pizza slices in nearby dorm rooms. Powered by zero-knowledge crust verification."
}

col_preset, col_btn = st.columns([3, 1])
with col_preset:
    selected_preset = st.selectbox("💡 Choose a Fast Demo Pitch Example:", list(preset_options.keys()))

default_pitch = preset_options[selected_preset] if selected_preset else ""

# Input Form
pitch_input = st.text_area(
    "Submit your startup pitch or executive summary:",
    value=default_pitch,
    height=110,
    placeholder="Describe your product, target customer, business model, and competitive advantage..."
)

col_run, col_clear = st.columns([1, 4])
with col_run:
    roast_clicked = st.button("🚀 Convene Committee", type="primary", use_container_width=True)

if roast_clicked:
    active_key = api_key_input.strip() or os.getenv("ANTHROPIC_API_KEY", "").strip()
    
    if not active_key:
        st.error("🔑 Please provide an Anthropic API Key in the sidebar or via .env")
    elif not pitch_input.strip():
        st.warning("⚠️ Please provide a startup pitch to evaluate!")
    else:
        client = anthropic.Anthropic(
            api_key=active_key,
            base_url="https://api.anthropic.com"
        )
        
        system_orchestrator = f"""
You are the PitchRoast Autonomous Investment Committee Syndicate consisting of 4 distinct AI partners:
1. Marc Low-res (General Partner): Cynical Silicon Valley Tier-1 VC. Attacks the TAM, market delusions, buzzwords, and lack of real moat.
2. Karen Burn-rate (Quantitative CFO): Ruthless Wall Street financial partner. Attacks unit economics, CAC vs LTV, negative margins, and runway delusions.
3. Torvalds-9000 (10x Grumpy CTO): Veteran architect who hates AI wrappers, technical debt, and pointless microservices.
4. Gordon Gekko AI (Syndicate Shark): Closing partner who delivers the ultimate verdict, metrics scores, and a satirical term sheet.

Roast Intensity Mode: {roast_mode}.
Analyze the pitch and return a valid JSON object with the exact keys:
{{
  "delusion_index": <int 0-100>,
  "moat_score": <int 0-10>,
  "runway_months": <int 1-12>,
  "pre_money_val": "<string funny valuation, e.g. '$42.50 and a lukewarm latte'>",
  "marc_critique": "<2-3 sentences sharp VC partner critique>",
  "karen_critique": "<2-3 sentences sharp CFO financial takedown>",
  "torvalds_critique": "<2-3 sentences sharp CTO technical dismantling>",
  "satirical_term_sheet": {{
    "valuation": "<string>",
    "investment_amount": "<string funny sum>",
    "liquidation_pref": "<e.g. 5x participating with board veto>",
    "covenants": [
      "<absurd clause 1>",
      "<absurd clause 2>",
      "<absurd clause 3>"
    ]
  }},
  "the_pivot": "<One surprisingly perceptive pivot idea that could actually work>"
}}
Ensure the tone is brilliant, hilarious, cynical, and Silicon Valley satire without violating safety policies. Return ONLY valid JSON.
"""

        with st.spinner(f"⚡ Convening the 4 partners via {selected_model}..."):
            try:
                response = client.messages.create(
                    model=selected_model,
                    max_tokens=2048,
                    system=system_orchestrator,
                    messages=[{"role": "user", "content": f"Pitch to evaluate:\n\n{pitch_input}"}]
                )
                
                # Extract text and optional thinking blocks
                thinking_text = ""
                main_text = ""
                for block in response.content:
                    if hasattr(block, "thinking"):
                        thinking_text += block.thinking
                    if hasattr(block, "text"):
                        main_text += block.text

                # Optional reasoning accordion for Opus
                if thinking_text:
                    with st.expander("🧠 VC Partner Deliberation (Claude Deep Extended Reasoning)", expanded=False):
                        st.markdown(f"```\n{thinking_text.strip()}\n```")

                # Parse JSON
                json_match = re.search(r'\{.*\}', main_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = json.loads(main_text)

                # Render Metrics Banner with animated styled cards
                st.markdown("### 📊 Syndicate Quantitative Scorecard")
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    d_val = data.get('delusion_index', 94)
                    st.markdown(f"""
                    <div class="metric-gauge-card">
                        <div class="metric-label-sub">Delusion Index</div>
                        <div class="metric-value-huge" style="color: #EF4444;">{d_val}%</div>
                        <div style="font-size: 0.75rem; color: #F87171;">🚨 Critically High</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m2:
                    m_val = data.get('moat_score', 1.0)
                    st.markdown(f"""
                    <div class="metric-gauge-card">
                        <div class="metric-label-sub">True Moat Score</div>
                        <div class="metric-value-huge" style="color: #F59E0B;">{m_val} / 10</div>
                        <div style="font-size: 0.75rem; color: #FCD34D;">⚡ Cloned in a weekend</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m3:
                    r_val = data.get('runway_months', 2)
                    st.markdown(f"""
                    <div class="metric-gauge-card">
                        <div class="metric-label-sub">Survival Runway</div>
                        <div class="metric-value-huge" style="color: #38BDF8;">{r_val} Mo</div>
                        <div style="font-size: 0.75rem; color: #7DD3FC;">⏳ Immediate cash crunch</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m4:
                    val_str = str(data.get('pre_money_val', "$12.00"))
                    st.markdown(f"""
                    <div class="metric-gauge-card">
                        <div class="metric-label-sub">Pre-Money Valuation</div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #A78BFA; min-height: 48px; display: flex; align-items: center; justify-content: center;">
                            {val_str}
                        </div>
                        <div style="font-size: 0.75rem; color: #C4B5FD;">📉 Non-negotiable haircut</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Render 3 Partner Cards
                st.markdown("### 🎙️ The Live Boardroom Debate")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("""
                    <div class="agent-card">
                        <div class="agent-header">
                            <span class="agent-badge badge-gp">General Partner</span>
                            <span style="font-size: 0.7rem; color: #10B981;">● VOTED PASS</span>
                        </div>
                        <div class="agent-name">🕶️ Marc Low-res</div>
                        <div class="agent-title">Lead Deal Partner & TAM Critic</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.55;">""" + 
                        str(data.get('marc_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c2:
                    st.markdown("""
                    <div class="agent-card">
                        <div class="agent-header">
                            <span class="agent-badge badge-cfo">Chief Financial Officer</span>
                            <span style="font-size: 0.7rem; color: #10B981;">● VOTED PASS</span>
                        </div>
                        <div class="agent-name">📊 Karen Burn-rate</div>
                        <div class="agent-title">Head of Unit Economics & Runway</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.55;">""" + 
                        str(data.get('karen_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)

                with c3:
                    st.markdown("""
                    <div class="agent-card">
                        <div class="agent-header">
                            <span class="agent-badge badge-cto">Chief Technology Officer</span>
                            <span style="font-size: 0.7rem; color: #10B981;">● VOTED PASS</span>
                        </div>
                        <div class="agent-name">💻 Torvalds-9000</div>
                        <div class="agent-title">Systems & Tech Debt Assassin</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.55;">""" + 
                        str(data.get('torvalds_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Satirical Term Sheet Card
                ts = data.get('satirical_term_sheet', {})
                covenants = ts.get('covenants', [])
                covenants_md = "\n".join([f"  [{i+1}] {c}" for i, c in enumerate(covenants)])
                
                term_sheet_text = f"""================================================================================
                    OFFICIAL SYNDICATE TERM SHEET (NON-BINDING)
================================================================================
TARGET COMPANY:      Founder Entity (Pre-Revenue / High-Anxiety)
SYNDICATE VALUATION: {ts.get('valuation', '$42.00 and an oat milk cappuccino')}
OFFERED INVESTMENT:  {ts.get('investment_amount', '$500 in AWS cloud credits')}
LIQUIDATION PREF:    {ts.get('liquidation_pref', '10x participating senior preferred')}

MANDATORY FOUNDER COVENANTS:
{covenants_md}

THE 1% REDEMPTION PIVOT (Actual path to revenue):
👉 {data.get('the_pivot', 'Pivot to selling shovelware to other AI founders.')}
================================================================================
"""
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📜 Syndicate Verdict & Non-Binding Term Sheet")
                
                st.markdown("""
                <div class="stamp-badge">❌ REJECTED BY SYNDICATE</div>
                """, unsafe_allow_html=True)
                
                st.code(term_sheet_text, language="yaml")

                # Action bar: Download + Token telemetry
                col_dl, col_usage = st.columns([1, 2])
                with col_dl:
                    st.download_button(
                        label="📥 Download Satirical Term Sheet (.txt)",
                        data=term_sheet_text,
                        file_name="PitchRoast_Term_Sheet.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col_usage:
                    st.caption(f"⚡ **Session Telemetry**: {response.usage.input_tokens} input tokens | {response.usage.output_tokens} output tokens | Model: `{selected_model}`")

            except Exception as e:  # noqa: BLE001
                st.error(f"Syndicate session error: {e!s}")
                st.info("Ensure your Anthropic API Key is active and has credits available.")
