import json
import os
import re

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="PitchRoast 🔥 | Multi-Agent Venture Syndicate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Dark UI Theme & Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus+Jakarta Sans', sans-serif;
    }
    
    .hero-container {
        text-align: center;
        padding: 1.8rem 1rem 1.2rem 1rem;
        background: linear-gradient(180deg, rgba(255, 69, 0, 0.08) 0%, rgba(0, 0, 0, 0) 100%);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255, 69, 0, 0.15);
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4500, #FF8C00, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.03em;
    }
    .hero-subtitle {
        color: #A0AEC0;
        font-size: 1.15rem;
        font-weight: 500;
        max-width: 700px;
        margin: 0 auto;
    }
    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        letter-spacing: 0.05em;
    }
    .badge-gp { background-color: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-cfo { background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-cto { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-shark { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    
    .agent-card {
        background: rgba(26, 32, 44, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        height: 100%;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .agent-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.2rem;
    }
    .agent-title {
        font-size: 0.8rem;
        color: #718096;
        margin-bottom: 0.8rem;
    }
    .term-sheet-box {
        background: #0F172A;
        border: 1px solid #F59E0B;
        border-radius: 12px;
        padding: 1.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🔥 PitchRoast Syndicate</div>
    <div class="hero-subtitle">Four autonomous AI venture partners debate, dismantle, and deliver the brutal truth no VC says to your face.</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Syndicate Settings")
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Use your event voucher key ($100 credit) from Epicenter."
    )
    
    model_choice = st.selectbox(
        "Frontier Model",
        [
            "claude-3-5-sonnet-20241022",
            "claude-opus-5-5",
            "claude-fable-5-1",
            "Custom..."
        ],
        index=0,
        help="Choose model. Opus 5.5 and Fable 5.1 can be chosen if enabled for your key."
    )
    
    if model_choice == "Custom...":
        selected_model = st.text_input("Model ID", value="claude-3-5-sonnet-20241022")
    else:
        selected_model = model_choice

    brutality = st.slider("Brutality Index (Temperature)", 0.2, 1.0, 0.85, 0.05)
    
    st.markdown("---")
    st.markdown("### 🏛️ Committee Members")
    st.markdown("• **🕶️ Marc Low-res** (General Partner)\n• **📊 Karen Burn-rate** (Quant CFO)\n• **💻 Torvalds-9000** (10x Grumpy CTO)\n• **🦈 Gordon Gekko AI** (Syndicate Shark)")
    
    st.markdown("---")
    st.caption("⚡ Built with Anthropic Claude for Stockholm Build Day at Epicenter.")

# Pitch Presets
preset_options = {
    "Select a pre-loaded startup idea or enter your own...": "",
    "☕ Autonomous Oat Milk Micro-Roastery with Web3 Proof-of-Foam": 
        "A decentralized network of countertop espresso machines that roast small-batch Nordic oat milk using on-chain temperature consensus. Users stake OAT tokens for latte art NFTs. Market size: $400B addressable beverage space.",
    "🤖 AI Meeting Proxy that says 'Blocked by Backend' in 14 accents": 
        "An autonomous AI agent avatar that joins daily Scrum standups on Zoom/Teams, randomly sighs, checks its phone, and responds 'I am blocked by the infrastructure backend' whenever your name is called. B2B SaaS priced at $49/engineer/month.",
    "🐾 Uber for Cats: Feline Scooter On-Demand": 
        "High-density urban cat affection. When an office worker feels burnt out, our app dispatches an autonomous electric scooter carrying a pre-vetted emotional support cat to their office lobby for a 15-minute petting session."
}

selected_preset = st.selectbox("💡 Choose a Fast Demo Example:", list(preset_options.keys()))

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
        
        system_orchestrator = """
You are the PitchRoast Autonomous Investment Committee Syndicate consisting of 4 distinct AI partners:
1. Marc Low-res (General Partner): Cynical Silicon Valley Tier-1 VC. Attacks the TAM, market delusions, buzzwords, and lack of real moat.
2. Karen Burn-rate (Quantitative CFO): Ruthless Wall Street financial partner. Attacks unit economics, CAC vs LTV, negative margins, and runway delusions.
3. Torvalds-9000 (10x Grumpy CTO): Veteran architect who hates AI wrappers, technical debt, and pointless microservices.
4. Gordon Gekko AI (Syndicate Shark): Closing partner who delivers the ultimate verdict, metrics scores, and a satirical term sheet.

Analyze the pitch and return a valid JSON object with the exact keys:
{
  "delusion_index": <int 0-100>,
  "moat_score": <int 0-10>,
  "runway_months": <int 1-12>,
  "pre_money_val": "<string funny valuation, e.g. '$42.50 and a lukewarm latte'>",
  "marc_critique": "<2-3 sentences sharp VC partner critique>",
  "karen_critique": "<2-3 sentences sharp CFO financial takedown>",
  "torvalds_critique": "<2-3 sentences sharp CTO technical dismantling>",
  "satirical_term_sheet": {
    "valuation": "<string>",
    "investment_amount": "<string funny sum>",
    "liquidation_pref": "<e.g. 5x participating with board veto>",
    "covenants": [
      "<absurd clause 1>",
      "<absurd clause 2>",
      "<absurd clause 3>"
    ]
  },
  "the_pivot": "<One surprisingly perceptive pivot idea that could actually work>"
}
Ensure the tone is brilliant, hilarious, cynical, and Silicon Valley satire without violating safety policies. Return ONLY valid JSON.
"""

        with st.spinner("⚡ Convening the 4 partners in the boardroom..."):
            try:
                response = client.messages.create(
                    model=selected_model,
                    max_tokens=1800,
                    temperature=brutality,
                    system=system_orchestrator,
                    messages=[{"role": "user", "content": f"Pitch to evaluate:\n\n{pitch_input}"}]
                )
                
                content = response.content[0].text
                
                # Robust JSON extraction
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = json.loads(content)

                # Render Metrics Banner
                st.markdown("### 📊 Syndicate Quantitative Scorecard")
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Delusion Index", f"{data.get('delusion_index', 94)}%", delta="Critically High", delta_color="inverse")
                with m2:
                    st.metric("Moat Score", f"{data.get('moat_score', 1.5)} / 10", delta="Easily cloned in a weekend", delta_color="inverse")
                with m3:
                    st.metric("Survival Runway", f"{data.get('runway_months', 2)} Months", delta="Immediate cash crunch", delta_color="inverse")
                with m4:
                    st.metric("Pre-Money Valuation", str(data.get('pre_money_val', "$12.00")))

                st.markdown("---")
                
                # Render 3 Partner Cards
                st.markdown("### 🎙️ The Live Boardroom Debate")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("""
                    <div class="agent-card">
                        <span class="agent-badge badge-gp">General Partner</span>
                        <div class="agent-name">🕶️ Marc Low-res</div>
                        <div class="agent-title">Lead Deal Partner & Ideology Critic</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;">""" + 
                        str(data.get('marc_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c2:
                    st.markdown("""
                    <div class="agent-card">
                        <span class="agent-badge badge-cfo">Chief Financial Officer</span>
                        <div class="agent-name">📊 Karen Burn-rate</div>
                        <div class="agent-title">Head of Portfolio Unit Economics</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;">""" + 
                        str(data.get('karen_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)

                with c3:
                    st.markdown("""
                    <div class="agent-card">
                        <span class="agent-badge badge-cto">Chief Technology Officer</span>
                        <div class="agent-name">💻 Torvalds-9000</div>
                        <div class="agent-title">Systems & Tech Debt Assassin</div>
                        <p style="color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;">""" + 
                        str(data.get('torvalds_critique', '')) + 
                        """</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Satirical Term Sheet Card
                ts = data.get('satirical_term_sheet', {})
                covenants = ts.get('covenants', [])
                covenants_md = "\n".join([f"- **Clause {i+1}**: {c}" for i, c in enumerate(covenants)])
                
                term_sheet_text = f"""
================================================================================
                    OFFICIAL SYNDICATE TERM SHEET (NON-BINDING)
================================================================================
TARGET COMPANY:      Founder Entity (Pre-Revenue / High-Anxiety)
SYNDICATE VALUATION: {ts.get('valuation', '$42.00 and an oat milk cappuccino')}
OFFERED INVESTMENT:  {ts.get('investment_amount', '$500 in AWS cloud credits')}
LIQUIDATION PREF:    {ts.get('liquidation_pref', '10x participating senior preferred')}

SPECIAL MANDATORY COVENANTS:
{covenants_md}

THE 1% REDEMPTION PIVOT:
👉 {data.get('the_pivot', 'Pivot to selling shovelware to other AI founders.')}
================================================================================
"""
                st.markdown("### 📜 Syndicate Verdict & Term Sheet")
                st.code(term_sheet_text, language="yaml")

                # Download button for demo export
                st.download_button(
                    label="📥 Export Term Sheet (.txt)",
                    data=term_sheet_text,
                    file_name="PitchRoast_Term_Sheet.txt",
                    mime="text/plain"
                )

            except Exception as e:  # noqa: BLE001
                st.error(f"Syndicate session error: {e!s}")
                st.info("Ensure your Anthropic API Key is active and has credits available.")
