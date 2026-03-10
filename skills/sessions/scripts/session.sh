#!/usr/bin/env bash
# session.sh — Helper for session API operations
# Usage: session.sh <command> [args...]
#
# Commands:
#   create   <workspaceId> <title> [type] [platform] [channelId] [threadId]
#   lookup   <platform> <channelId> <threadId>
#   get      <sessionId> [--events] [--event-limit N]
#   update   <sessionId> <json-body>
#   event    <sessionId> <type> [content] [metadata-json]
#   messages <sessionId> [limit]
#   list     <workspaceId> [--status S] [--type T] [--limit N]

set -euo pipefail

# Load API URL from environment or .env file
if [ -z "${VIRALFARM_API_URL:-}" ]; then
  ENV_FILE="${HOME}/.clawdbot/.env"
  if [ -f "$ENV_FILE" ]; then
    VIRALFARM_API_URL=$(grep '^VIRALFARM_API_URL=' "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'")
  fi
fi

if [ -z "${VIRALFARM_API_URL:-}" ]; then
  echo "Error: VIRALFARM_API_URL not set. Add it to ~/.clawdbot/.env" >&2
  exit 1
fi

API="${VIRALFARM_API_URL}"
AUTH_HEADER=""
if [ -n "${VIRALFARM_API_KEY:-}" ]; then
  AUTH_HEADER="-H \"Authorization: Bearer ${VIRALFARM_API_KEY}\""
fi

cmd="${1:-help}"
shift || true

case "$cmd" in
  create)
    WORKSPACE_ID="${1:?workspace ID required}"
    TITLE="${2:?title required}"
    TYPE="${3:-general}"
    PLATFORM="${4:-}"
    CHANNEL_ID="${5:-}"
    THREAD_ID="${6:-}"

    BODY="{\"workspaceId\":\"$WORKSPACE_ID\",\"title\":\"$TITLE\",\"type\":\"$TYPE\""
    [ -n "$PLATFORM" ] && BODY="$BODY,\"platform\":\"$PLATFORM\""
    [ -n "$CHANNEL_ID" ] && BODY="$BODY,\"platformChannelId\":\"$CHANNEL_ID\""
    [ -n "$THREAD_ID" ] && BODY="$BODY,\"platformThreadId\":\"$THREAD_ID\""
    BODY="$BODY}"

    curl -s -X POST "$API/sessions" \
      -H "Content-Type: application/json" \
      -d "$BODY" | python3 -m json.tool 2>/dev/null || cat
    ;;

  lookup)
    PLATFORM="${1:?platform required}"
    CHANNEL_ID="${2:?channelId required}"
    THREAD_ID="${3:?threadId required}"

    curl -s "$API/sessions/lookup?platform=$PLATFORM&platformChannelId=$CHANNEL_ID&platformThreadId=$THREAD_ID" \
      | python3 -m json.tool 2>/dev/null || cat
    ;;

  get)
    SESSION_ID="${1:?session ID required}"
    shift
    PARAMS=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --events) PARAMS="${PARAMS:+$PARAMS&}includeEvents=true" ;;
        --event-limit) shift; PARAMS="${PARAMS:+$PARAMS&}eventLimit=$1" ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
      esac
      shift
    done

    URL="$API/sessions/$SESSION_ID"
    [ -n "$PARAMS" ] && URL="$URL?$PARAMS"

    curl -s "$URL" | python3 -m json.tool 2>/dev/null || cat
    ;;

  update)
    SESSION_ID="${1:?session ID required}"
    BODY="${2:?JSON body required}"

    curl -s -X PATCH "$API/sessions/$SESSION_ID" \
      -H "Content-Type: application/json" \
      -d "$BODY" | python3 -m json.tool 2>/dev/null || cat
    ;;

  event)
    SESSION_ID="${1:?session ID required}"
    TYPE="${2:?event type required}"
    CONTENT="${3:-}"
    METADATA="${4:-}"

    BODY="{\"type\":\"$TYPE\""
    [ -n "$CONTENT" ] && BODY="$BODY,\"content\":\"$CONTENT\""
    [ -n "$METADATA" ] && BODY="$BODY,\"metadata\":$METADATA"
    BODY="$BODY}"

    curl -s -X POST "$API/sessions/$SESSION_ID/events" \
      -H "Content-Type: application/json" \
      -d "$BODY" | python3 -m json.tool 2>/dev/null || cat
    ;;

  messages)
    SESSION_ID="${1:?session ID required}"
    LIMIT="${2:-100}"

    curl -s "$API/sessions/$SESSION_ID/messages?limit=$LIMIT" \
      | python3 -m json.tool 2>/dev/null || cat
    ;;

  list)
    WORKSPACE_ID="${1:?workspace ID required}"
    shift
    PARAMS="workspaceId=$WORKSPACE_ID"
    while [ $# -gt 0 ]; do
      case "$1" in
        --status) shift; PARAMS="$PARAMS&status=$1" ;;
        --type) shift; PARAMS="$PARAMS&type=$1" ;;
        --limit) shift; PARAMS="$PARAMS&limit=$1" ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
      esac
      shift
    done

    curl -s "$API/sessions?$PARAMS" | python3 -m json.tool 2>/dev/null || cat
    ;;

  help|*)
    echo "session.sh — Session API helper"
    echo ""
    echo "Usage: session.sh <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  create   <workspaceId> <title> [type] [platform] [channelId] [threadId]"
    echo "  lookup   <platform> <channelId> <threadId>"
    echo "  get      <sessionId> [--events] [--event-limit N]"
    echo "  update   <sessionId> <json-body>"
    echo "  event    <sessionId> <type> [content] [metadata-json]"
    echo "  messages <sessionId> [limit]"
    echo "  list     <workspaceId> [--status S] [--type T] [--limit N]"
    echo ""
    echo "Environment:"
    echo "  VIRALFARM_API_URL  — API base URL (loaded from ~/.clawdbot/.env)"
    echo "  VIRALFARM_API_KEY  — Optional Bearer token"
    ;;
esac
