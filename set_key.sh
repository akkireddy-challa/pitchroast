#!/usr/bin/env bash
# Quick helper to configure your Anthropic API key for this project.
# Updates ANTHROPIC_API_KEY in .env in place, preserving every other variable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "${1:-}" ]]; then
    echo "Usage: ./set_key.sh <your-anthropic-api-key>"
    exit 1
fi

KEY="$1"
ENV_FILE=".env"

# Event keys can vary in format, so warn rather than refuse.
if [[ "$KEY" != sk-ant-* ]]; then
    echo "⚠️  Heads up: that does not look like an Anthropic key (expected a 'sk-ant-' prefix)."
    echo "   Continuing anyway - event keys can differ."
fi

TMP_FILE="$(mktemp "${TMPDIR:-/tmp}/pitchroast-env.XXXXXX")"
trap 'rm -f "$TMP_FILE"' EXIT
chmod 600 "$TMP_FILE"

[[ -f "$ENV_FILE" ]] || : > "$ENV_FILE"
chmod 600 "$ENV_FILE"

# upsert VAR VALUE - replace the first assignment of VAR, keep all other lines
# (comments, blank lines and unrelated variables) exactly as they were.
upsert() {
    local var="$1" value="$2" found=0 line
    : > "$TMP_FILE"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ $found -eq 0 && "$line" =~ ^[[:space:]]*(export[[:space:]]+)?${var}[[:space:]]*= ]]; then
            printf '%s="%s"\n' "$var" "$value" >> "$TMP_FILE"
            found=1
        else
            printf '%s\n' "$line" >> "$TMP_FILE"
        fi
    done < "$ENV_FILE"

    if [[ $found -eq 0 ]]; then
        printf '%s="%s"\n' "$var" "$value" >> "$TMP_FILE"
    fi

    cat "$TMP_FILE" > "$ENV_FILE"
}

upsert "ANTHROPIC_API_KEY" "$KEY"
# Pin the public API so the corporate LiteLLM proxy is bypassed (see .env.example).
upsert "ANTHROPIC_BASE_URL" "https://api.anthropic.com"

chmod 600 "$ENV_FILE"

# Never print the full key.
echo "✅ ANTHROPIC_API_KEY updated in $SCRIPT_DIR/$ENV_FILE (${KEY:0:11}... , mode 600)"

if [[ -x .venv/bin/python ]]; then
    echo "📡 Verifying key..."
    .venv/bin/python test_connection.py
else
    echo "ℹ️  No .venv yet - run 'make install', then 'make test' to verify the key."
fi
