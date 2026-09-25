#!/usr/bin/env python3
"""
PitchRoast 🔥 - Full Syndicate Live Demo Runner
Executes an end-to-end investment committee session using Anthropic's public API
and records spans in Arize Phoenix OSS observability.
"""
import json
import os
import re
import sys
import time

import anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ Error: ANTHROPIC_API_KEY not found in .env")
    sys.exit(1)

print("=" * 80)
print("🔥 PITCHROAST: THE AUTONOMOUS VENTURE COMMITTEE")
print("=" * 80)
print(f"🔑 Key Active: {api_key[:14]}...{api_key[-6:]}")
print("🌐 Target API: https://api.anthropic.com")

# Initialize Phoenix Observability
print("\n🔭 Initializing Arize Phoenix OSS Observability...")
try:
    import phoenix as px
    from openinference.instrumentation.anthropic import AnthropicInstrumentor
    session = px.launch_app(run_in_thread=True)
    AnthropicInstrumentor().instrument()
    print(f"✅ Arize Phoenix Tracing Active at: {session.url}")
except Exception as e:  # noqa: BLE001
    print(f"⚠️ Phoenix notice: {e}")

# Sample Stockholm Hackathon Startup Pitch
pitch = (
    "Autonomous Oat Milk Micro-Roastery with Web3 Proof-of-Foam: "
    "A decentralized network of countertop espresso machines that roast small-batch Nordic oat milk "
    "using on-chain temperature consensus. Users stake OAT tokens for latte art NFTs. "
    "Market size: $400B addressable beverage space."
)

print("\n📋 SUBMITTED STARTUP PITCH:")
print(f"👉 \"{pitch}\"\n")

model_choice = "claude-fable-5-1"
print(f"⚡ Convening the 4-Partner Investment Syndicate via {model_choice}...")

client = anthropic.Anthropic(
    api_key=api_key,
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

start_time = time.time()
try:
    response = client.messages.create(
        model=model_choice,
        max_tokens=2048,
        system=system_orchestrator,
        messages=[{"role": "user", "content": f"Pitch to evaluate:\n\n{pitch}"}]
    )
    elapsed = time.time() - start_time
    
    main_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    json_match = re.search(r'\{.*\}', main_text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
    else:
        data = json.loads(main_text)

    print("\n" + "=" * 80)
    print("📊 SYNDICATE QUANTITATIVE SCORECARD")
    print("=" * 80)
    print(f"• Delusion Index:     {data.get('delusion_index')}% (Critically High)")
    print(f"• True Moat Score:    {data.get('moat_score')} / 10 (Zero defensibility)")
    print(f"• Projected Runway:   {data.get('runway_months')} Months (Emergency cash crunch)")
    print(f"• Pre-Money Valuation:{data.get('pre_money_val')}")

    print("\n" + "=" * 80)
    print("🎙️ THE BOARDROOM DEBATE")
    print("=" * 80)
    print(f"\n🕶️ [MARC LOW-RES | General Partner]:\n{data.get('marc_critique')}")
    print(f"\n📊 [KAREN BURN-RATE | Quant CFO]:\n{data.get('karen_critique')}")
    print(f"\n💻 [TORVALDS-9000 | Systems CTO]:\n{data.get('torvalds_critique')}")

    ts = data.get('satirical_term_sheet', {})
    print("\n" + "=" * 80)
    print("📜 OFFICIAL SYNDICATE TERM SHEET")
    print("=" * 80)
    print(f"• VALUATION:        {ts.get('valuation')}")
    print(f"• INVESTMENT:       {ts.get('investment_amount')}")
    print(f"• LIQUIDATION PREF: {ts.get('liquidation_pref')}")
    print("• MANDATORY FOUNDER COVENANTS:")
    for idx, cov in enumerate(ts.get('covenants', [])):
        print(f"   [{idx + 1}] {cov}")
    print(f"\n💡 THE 1% PIVOT (Actual path to revenue):\n👉 {data.get('the_pivot')}")
    
    print("\n" + "=" * 80)
    print("⚡ SESSION TELEMETRY & OBSERVABILITY")
    print("=" * 80)
    print(f"• Latency:       {elapsed:.2f}s")
    print(f"• Input Tokens:  {response.usage.input_tokens}")
    print(f"• Output Tokens: {response.usage.output_tokens}")
    print(f"• Total Tokens:  {response.usage.input_tokens + response.usage.output_tokens}")
    print("• Arize Phoenix: Traces recorded at http://localhost:6006")
    print("=" * 80)
    print("✅ DEMO COMPLETED SUCCESSFULLY!\n")

except Exception as e:  # noqa: BLE001
    print(f"❌ Error during syndicate execution: {e}")
    sys.exit(1)
