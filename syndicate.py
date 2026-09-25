"""
PitchRoast 🔥 - Syndicate Core Engine
Single Source of Truth for investment committee personas, prompting, validation, and execution.
"""
import html
import json
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

# System Orchestration Prompt
SYSTEM_PROMPT = """You are the PitchRoast Autonomous Investment Committee Syndicate consisting of 4 distinct AI partners:
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
Ensure the tone is brilliant, hilarious, cynical, and Silicon Valley satire without violating safety policies. The satire targets the pitch and business model, never real protected attributes. Return ONLY valid JSON."""

def build_system_prompt(brutality_mode: str = "Standard Sand Hill Roast") -> str:
    """Injects dynamic brutality mode into the system prompt."""
    return f"{SYSTEM_PROMPT}\n\nRoast Intensity Directive: Mode is '{brutality_mode}'. Adjust savageness and realism accordingly."

def evaluate_pitch(
    pitch: str,
    api_key: str | None = None,
    model: str = "claude-fable-5-1",
    brutality_mode: str = "Standard Sand Hill Roast"
) -> dict[str, Any]:
    """
    Executes a syndicate committee evaluation using Anthropic's public API.
    Returns parsed dictionary with escaped critique text and execution metadata.
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        msg = "Anthropic API Key not found. Please provide an active event key."
        raise ValueError(msg)

    client = anthropic.Anthropic(
        api_key=key,
        base_url="https://api.anthropic.com"
    )

    system_prompt = build_system_prompt(brutality_mode)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Startup pitch to evaluate:\n\n{pitch}"}]
    )

    # Check for refusal
    if getattr(response, "stop_reason", None) == "refusal":
        return {
            "refused": True,
            "refusal_reason": "The Syndicate has summarily recused itself from this meeting under SEC Rule 10b-5.",
            "usage": response.usage,
            "model": model,
        }

    # Extract text and thinking blocks
    thinking_text = ""
    main_text = ""
    for block in response.content:
        if hasattr(block, "thinking"):
            thinking_text += block.thinking
        if hasattr(block, "text"):
            main_text += block.text

    # Parse JSON output
    json_match = re.search(r'\{.*\}', main_text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
    else:
        data = json.loads(main_text)

    # Sanitize and HTML-escape text to prevent XSS or broken layout
    data["marc_critique_safe"] = html.escape(str(data.get("marc_critique", "")))
    data["karen_critique_safe"] = html.escape(str(data.get("karen_critique", "")))
    data["torvalds_critique_safe"] = html.escape(str(data.get("torvalds_critique", "")))
    data["the_pivot_safe"] = html.escape(str(data.get("the_pivot", "")))
    data["thinking_text"] = thinking_text
    data["usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
    }
    data["model"] = model
    data["refused"] = False

    return data
