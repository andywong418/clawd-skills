#!/usr/bin/env bash
set -eo pipefail

# Load env
ENV_FILE="${HOME}/.clawdbot/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

API_URL="${SEEDANCE_API_URL:?SEEDANCE_API_URL not set in ~/.clawdbot/.env}"
WORKSPACE_ID="${SEEDANCE_WORKSPACE_ID:?SEEDANCE_WORKSPACE_ID not set in ~/.clawdbot/.env}"
API_KEY="${SEEDANCE_API_KEY:-}"

AUTH_HEADER=""
if [ -n "$API_KEY" ]; then
  AUTH_HEADER="Authorization: Bearer $API_KEY"
fi

CMD="${1:?Usage: api.sh <command> [args]}"
shift

case "$CMD" in
  create-session)
    TITLE="" TYPE="video_creation" CHANNEL_ID="" THREAD_ID=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --title) TITLE="$2"; shift 2 ;;
        --type) TYPE="$2"; shift 2 ;;
        --channel-id) CHANNEL_ID="$2"; shift 2 ;;
        --thread-id) THREAD_ID="$2"; shift 2 ;;
        *) shift ;;
      esac
    done

    BODY=$(jq -n \
      --arg wid "$WORKSPACE_ID" \
      --arg title "$TITLE" \
      --arg type "$TYPE" \
      --arg channelId "$CHANNEL_ID" \
      --arg threadId "$THREAD_ID" \
      '{
        workspaceId: $wid,
        title: $title,
        type: $type,
        platform: "slack",
        platformChannelId: $channelId,
        platformThreadId: $threadId
      }')

    curl -s -X POST "$API_URL/sessions" \
      -H "Content-Type: application/json" \
      ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
      -d "$BODY"
    ;;

  add-event)
    SESSION_ID="${1:?Session ID required}"
    shift
    TYPE="message" ROLE="" CONTENT="" META="{}"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --type) TYPE="$2"; shift 2 ;;
        --role) ROLE="$2"; shift 2 ;;
        --content) CONTENT="$2"; shift 2 ;;
        --metadata) META="$2"; shift 2 ;;
        *) shift ;;
      esac
    done

    BODY=$(jq -n \
      --arg type "$TYPE" \
      --arg role "$ROLE" \
      --arg content "$CONTENT" \
      --argjson metadata "$META" \
      '{type: $type, content: $content, metadata: $metadata} + (if $role != "" then {role: $role} else {} end)')

    curl -s -X POST "$API_URL/sessions/$SESSION_ID/events" \
      -H "Content-Type: application/json" \
      ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
      -d "$BODY"
    ;;

  get-session)
    SESSION_ID="${1:?Session ID required}"
    curl -s "$API_URL/sessions/$SESSION_ID?includeEvents=true" \
      ${AUTH_HEADER:+-H "$AUTH_HEADER"}
    ;;

  list-sessions)
    curl -s "$API_URL/sessions?workspaceId=$WORKSPACE_ID" \
      ${AUTH_HEADER:+-H "$AUTH_HEADER"}
    ;;

  *)
    echo "Unknown command: $CMD"
    echo "Commands: create-session, add-event, get-session, list-sessions"
    exit 1
    ;;
esac
