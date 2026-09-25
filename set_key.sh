#!/usr/bin/env bash
# Quick helper to configure your API key across all terminals
if [[ -z "${1:-}" ]]; then
    echo "Usage: ./set_key.sh <your-anthropic-api-key>"
    exit 1
fi

KEY="$1"
echo "ANTHROPIC_API_KEY=\"$KEY\"" > .env
echo "ANTHROPIC_BASE_URL=\"https://api.anthropic.com\"" >> .env
echo "✅ Saved key to $(pwd)/.env"
echo "📡 Verifying key..."
./test_connection.py
