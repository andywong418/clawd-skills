#!/bin/bash
# Add memory to supermemory
# Usage: ./add-memory.sh "content to remember" [--user USER_ID]

set -e

source ~/.clawdbot/.env

CONTENT="$1"
USER=""
BOT_ID="${SUPERMEMORY_BOT_ID:-naruto}"

if [[ -z "$CONTENT" ]]; then
  echo "Usage: ./add-memory.sh \"content to remember\" [--user USER_ID]"
  exit 1
fi

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

# Escape content for JSON
ESCAPED_CONTENT=$(echo "$CONTENT" | jq -Rs '.')

# Add to supermemory
RESPONSE=$(curl -s -X POST "https://api.supermemory.ai/v3/documents" \
  -H "Authorization: Bearer $SUPERMEMORY_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": $ESCAPED_CONTENT,
    \"containerTag\": \"$CONTAINER_TAG\"
  }")

# Check response
if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ Memory stored in: $CONTAINER_TAG"
  echo "   ID: $(echo "$RESPONSE" | jq -r '.id')"
else
  echo "❌ Failed to store memory"
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
