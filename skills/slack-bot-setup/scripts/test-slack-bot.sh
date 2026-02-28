#!/bin/bash
# Test a Slack bot token and its capabilities
# Usage: ./test-slack-bot.sh <bot-token> [user-id-to-dm]

set -e

TOKEN="${1:?Usage: $0 <bot-token> [user-id-to-dm]}"
USER_ID="${2:-}"

echo "=== Testing Slack Bot Token ==="
echo

# Test auth
echo "1. Checking auth..."
AUTH=$(curl -s -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $TOKEN")

if echo "$AUTH" | jq -e '.ok == true' > /dev/null 2>&1; then
  echo "   ✓ Token valid"
  echo "   Bot: $(echo "$AUTH" | jq -r '.user')"
  echo "   Team: $(echo "$AUTH" | jq -r '.team')"
  BOT_ID=$(echo "$AUTH" | jq -r '.user_id')
else
  echo "   ✗ Token invalid: $(echo "$AUTH" | jq -r '.error')"
  exit 1
fi
echo

# Check scopes by testing endpoints
echo "2. Checking scopes..."

# users:read
USERS=$(curl -s "https://slack.com/api/users.list?limit=3" \
  -H "Authorization: Bearer $TOKEN")
if echo "$USERS" | jq -e '.ok == true' > /dev/null 2>&1; then
  echo "   ✓ users:read - Can list users"
  USER_COUNT=$(echo "$USERS" | jq '.members | length')
  echo "     Found $USER_COUNT users (limited to 3)"
else
  echo "   ✗ users:read - Missing scope"
fi

# channels:read
CHANNELS=$(curl -s "https://slack.com/api/conversations.list?types=public_channel&limit=3" \
  -H "Authorization: Bearer $TOKEN")
if echo "$CHANNELS" | jq -e '.ok == true' > /dev/null 2>&1; then
  echo "   ✓ channels:read - Can list channels"
else
  echo "   ✗ channels:read - Missing scope"
fi

# im:write (test by opening DM with self or provided user)
if [ -n "$USER_ID" ]; then
  DM=$(curl -s -X POST https://slack.com/api/conversations.open \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"users\": \"$USER_ID\"}")
  if echo "$DM" | jq -e '.ok == true' > /dev/null 2>&1; then
    echo "   ✓ im:write - Can open DMs"
    DM_CHANNEL=$(echo "$DM" | jq -r '.channel.id')
    echo "     DM channel: $DM_CHANNEL"
    
    # Test chat:write
    MSG=$(curl -s -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"channel\": \"$DM_CHANNEL\", \"text\": \"🤖 Bot test message\"}")
    if echo "$MSG" | jq -e '.ok == true' > /dev/null 2>&1; then
      echo "   ✓ chat:write - Can send messages"
    else
      echo "   ✗ chat:write - $(echo "$MSG" | jq -r '.error')"
    fi
  else
    echo "   ✗ im:write - $(echo "$DM" | jq -r '.error')"
  fi
else
  echo "   ? im:write - Provide user ID to test DM capability"
fi

echo
echo "=== Test Complete ==="
