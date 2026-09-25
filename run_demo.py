#!/usr/bin/env python3
"""
PitchRoast 🔥 - Full Syndicate Live Demo Runner
Executes an end-to-end investment committee session using Anthropic's public API
and records spans in Arize Phoenix OSS observability.
"""
import os
import sys
import time

from dotenv import load_dotenv

from syndicate import evaluate_pitch

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

start_time = time.time()
try:
    data = evaluate_pitch(
        pitch=pitch,
        api_key=api_key,
        model=model_choice,
        brutality_mode="Standard Sand Hill Roast"
    )
    elapsed = time.time() - start_time

    if data.get("refused"):
        print("\n🛑 The Syndicate declined to take this meeting.")
        print(data.get("refusal_reason"))
        sys.exit(0)

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
    
    usage = data.get("usage", {})
    print("\n" + "=" * 80)
    print("⚡ SESSION TELEMETRY & OBSERVABILITY")
    print("=" * 80)
    print(f"• Latency:       {elapsed:.2f}s")
    print(f"• Input Tokens:  {usage.get('input_tokens')}")
    print(f"• Output Tokens: {usage.get('output_tokens')}")
    print(f"• Total Tokens:  {usage.get('total_tokens')}")
    print("• Arize Phoenix: Traces recorded at http://localhost:6006")
    print("=" * 80)
    print("✅ DEMO COMPLETED SUCCESSFULLY!\n")

except Exception as e:  # noqa: BLE001
    print(f"❌ Error during syndicate execution: {e}")
    sys.exit(1)
