#!/usr/bin/env bash
# Run a warmup session for all accounts sequentially.
# Usage: bash run_all_now.sh [duration_minutes]
# Sends Slack notification when complete.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DURATION="${1:-5}"

source ~/.clawdbot/.env 2>/dev/null || true
export DISPLAY="${DISPLAY:-:99}"

accounts=(
  "instagram_viralfarmai"
  "instagram_timetwopop"
  "tiktok_viralfarm.ai"
  "twitter_viralfarmbot"
)

passed=0
failed=0
results=""

for account in "${accounts[@]}"; do
  echo "[$(date -u '+%H:%M UTC')] ▶ $account"
  if python3 "$SCRIPT_DIR/session_runner.py" --account "$account" --duration "$DURATION" 2>&1; then
    python3 "$SCRIPT_DIR/warmup.py" --account "$account" done 2>&1
    echo "[$(date -u '+%H:%M UTC')] ✓ $account done"
    results="${results}✓ ${account}\n"
    ((passed++)) || true
  else
    echo "[$(date -u '+%H:%M UTC')] ✗ $account failed"
    results="${results}✗ ${account} (failed)\n"
    ((failed++)) || true
  fi
done

# Slack notification
TOKEN="${SLACK_BOT_TOKEN:-}"
if [ -n "$TOKEN" ]; then
  MSG="🦠 *Warmup complete* — ${passed}/${#accounts[@]} sessions done\n\`\`\`\n${results}\`\`\`"
  curl -s -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"channel\":\"C0AHBK5E9V3\",\"text\":\"$(echo -e "$MSG" | sed 's/"/\\"/g')\"}" > /dev/null
fi

echo "[$(date -u '+%H:%M UTC')] All done — ${passed} passed, ${failed} failed"
