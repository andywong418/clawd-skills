#!/bin/bash
# Fetch a tweet by ID or URL
# Usage: fetch_tweet.sh <tweet_id_or_url>

set -e

INPUT="$1"
if [[ -z "$INPUT" ]]; then
    echo "Usage: fetch_tweet.sh <tweet_id_or_url>" >&2
    exit 1
fi

# Extract tweet ID from various URL formats
# Handles: twitter.com/user/status/ID, x.com/user/status/ID, or just ID
if [[ "$INPUT" =~ /status/([0-9]+) ]]; then
    TWEET_ID="${BASH_REMATCH[1]}"
elif [[ "$INPUT" =~ ^[0-9]+$ ]]; then
    TWEET_ID="$INPUT"
else
    echo "Error: Could not extract tweet ID from: $INPUT" >&2
    exit 1
fi

# Source credentials if not already set
if [[ -z "$TWITTER_BEARER_TOKEN" ]]; then
    source ~/.clawdbot/.env 2>/dev/null || {
        echo "Error: Could not load credentials from ~/.clawdbot/.env" >&2
        exit 1
    }
fi

# Fetch tweet with expansions
curl -s -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
    "https://api.twitter.com/2/tweets/${TWEET_ID}?tweet.fields=text,author_id,created_at,public_metrics,conversation_id&expansions=author_id&user.fields=username,name,verified"
