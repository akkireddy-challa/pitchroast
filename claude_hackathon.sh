#!/usr/bin/env bash
# Run Claude Code CLI strictly with your personal / event key.
# Bypasses Telia LiteLLM, internal proxies, and company virtual keys.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "⚠️  ANTHROPIC_API_KEY is not set."
    echo "Export it first:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "or put it in $SCRIPT_DIR/.env"
    exit 1
fi

export ANTHROPIC_BASE_URL="https://api.anthropic.com"
unset ANTHROPIC_CUSTOM_HEADERS

echo "🚀 Starting Claude Code pointing to public api.anthropic.com (Key: ${ANTHROPIC_API_KEY:0:12}...)"
exec claude --setting-sources project,local "$@"
