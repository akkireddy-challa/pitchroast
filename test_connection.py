#!/usr/bin/env python3
"""
Quick test script to verify your Anthropic API Key.
Tests against event-enabled models: claude-fable-5-1 and claude-opus-5-5.
"""
import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY is not set.")
    print("Set it via:")
    print("  export ANTHROPIC_API_KEY='sk-ant-...'")
    print("or create a .env file with ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

print(f"🔑 Key detected (prefix: {api_key[:14]}...)")
print("📡 Connecting to Anthropic public API...")

client = anthropic.Anthropic(
    api_key=api_key,
    base_url="https://api.anthropic.com"
)

try:
    response = client.messages.create(
        model="claude-fable-5-1",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'Stockholm Epicenter Ready!' and nothing else."}]
    )
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    print("✅ Success! Response received from claude-fable-5-1:")
    print(f"👉 {text.strip()}")
    print(f"📊 Usage: {response.usage.input_tokens} input tokens, {response.usage.output_tokens} output tokens")
except anthropic.APIError as e:
    print(f"❌ Anthropic API call failed: {e}")
    sys.exit(1)
except Exception as e:  # noqa: BLE001
    print(f"❌ Unexpected failure: {e}")
    sys.exit(1)
