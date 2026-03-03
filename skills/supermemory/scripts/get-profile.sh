#!/bin/bash
# Get profile from supermemory (without search query)
# Usage: ./get-profile.sh [--user USER_ID]

set -e

source ~/.clawdbot/.env

USER=""
BOT_ID="${SUPERMEMORY_BOT_ID:-naruto}"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --user) USER="$2"; shift 2 ;;
    --bot) BOT_ID="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Build container tag
if [[ -n "$USER" ]]; then
  CONTAINER_TAG="${BOT_ID}:user:${USER}"
else
  CONTAINER_TAG="${BOT_ID}"
fi

# Query supermemory
RESPONSE=$(curl -s -X POST "https://api.supermemory.ai/v4/profile" \
  -H "Authorization: Bearer $SUPERMEMORY_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"containerTag\": \"$CONTAINER_TAG\"
  }")

# Parse and format output
echo "=== Supermemory Profile: $CONTAINER_TAG ==="
echo ""
echo "📋 Static Facts (long-term):"
echo "$RESPONSE" | jq -r '.profile.static[]?' 2>/dev/null || echo "  (none yet)"
if [[ $(echo "$RESPONSE" | jq '.profile.static | length' 2>/dev/null) == "0" ]]; then
  echo "  (none yet)"
fi
echo ""
echo "🔄 Dynamic Context (recent):"
echo "$RESPONSE" | jq -r '.profile.dynamic[]?' 2>/dev/null || echo "  (none yet)"
if [[ $(echo "$RESPONSE" | jq '.profile.dynamic | length' 2>/dev/null) == "0" ]]; then
  echo "  (none yet)"
fi
