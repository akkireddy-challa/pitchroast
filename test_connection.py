#!/usr/bin/env python3
"""
Quick test script to verify your Anthropic API Key once obtained tonight.
Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python test_connection.py
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

print(f"🔑 Key detected (prefix: {api_key[:12]}...)")
print("📡 Testing connection with Anthropic API...")

client = anthropic.Anthropic(
    api_key=api_key,
    base_url="https://api.anthropic.com"
)

try:
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say hello from Stockholm Epicenter Build Day in 5 words."}]
    )
    print("✅ Success! Response received:")
    print(f"👉 {response.content[0].text.strip()}")
except anthropic.APIError as e:
    print(f"❌ Anthropic API call failed: {e}")
    sys.exit(1)
except Exception as e:  # noqa: BLE001
    print(f"❌ Unexpected failure: {e}")
    sys.exit(1)
