#!/bin/bash
# Get context from supermemory (profile + relevant memories)
# Usage: ./get-context.sh "query" [--user USER_ID]

set -e

source ~/.clawdbot/.env

QUERY="$1"
USER=""
BOT_ID="${SUPERMEMORY_BOT_ID:-naruto}"

# Parse args
shift || true
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
    \"containerTag\": \"$CONTAINER_TAG\",
    \"q\": \"$QUERY\"
  }")

# Parse and format output
echo "=== Supermemory Context for: $CONTAINER_TAG ==="
echo ""
echo "📋 Static Facts:"
echo "$RESPONSE" | jq -r '.profile.static[]? // "No static facts yet"' 2>/dev/null || echo "No static facts yet"
echo ""
echo "🔄 Dynamic Context:"
echo "$RESPONSE" | jq -r '.profile.dynamic[]? // "No dynamic context yet"' 2>/dev/null || echo "No dynamic context yet"
echo ""
echo "🔍 Relevant Memories:"
echo "$RESPONSE" | jq -r '.searchResults.results[]?.memory // "No relevant memories"' 2>/dev/null || echo "No relevant memories"
